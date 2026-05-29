"""Resolve a candidate livery zip to its aircraft + slugs.

Uploaders have wildly different packaging habits, so the pipeline has
to cope with every shape a livery can arrive in:

  - **structural / Liveries-rooted** -- the DCS-native shape, with an
    authoritative `Liveries/<Aircraft>/<slug>/` path. The wrapper above
    `Liveries/` (if any) is irrelevant (OvGME packs name it after the
    pack, e.g. `Death Dealers - Chaos/Liveries/FA-18C_hornet/...`).
  - **structural / aircraft-folder** -- `<Aircraft>/<slug>/...` with the
    top folder being a known aircraft (the old "single-livery upload").
  - **bare** -- just `<slug>/description.lua` + textures, no aircraft
    folder anywhere (e.g. `_VFA-103 Jolly Rogers - CAG/...`). Here the
    aircraft can only be *inferred*.

Resolution is structural-first (the `Liveries/<X>/` or `<X>/` folder
name is authoritative -- DCS itself uses it to bind a livery to an
aircraft), and only falls back to inference for bare uploads.

Inference is deliberately conservative. We collect every signal we
have for a bare slug -- the slug folder name, the texture/file names
inside it, the description.lua text, and the original upload filename
-- and substring-match each against the per-aircraft token table in
aircraft.json. The decision rule is binary:

    union of matched canonical aircraft == 1  -> resolve
    union == 0 (nothing matched) or > 1 (ambiguous) -> REJECT to staff

There is no confidence score and no "best guess". Silent mis-routing
to the wrong aircraft is worse than a reject-with-guidance, so anything
the rule can't pin down unambiguously becomes a Finding and the upload
goes to the staff channel instead of being published.

This is the scanner's layout gate: scan.py runs resolve() after the
tier-1 integrity gate, folds any Findings into the Verdict (so an
unresolvable layout fails the scan and routes to reject.py), and
stashes the resolved layout in the Verdict for publish.py to consume.
"""

from __future__ import annotations

import dataclasses
import json
import re
import zipfile
from pathlib import Path

from .verdict import Finding

LAYOUT_TIER = 7

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "aircraft.json"

_NORM_RE = re.compile(r"[^a-z0-9]+")


def _norm(s: str) -> str:
    """Lower-case and drop every non-alphanumeric char.

    So `FA-18C_hornet`, `fa-18c`, and `FA 18C` all collapse to
    `fa18chornet` / `fa18c`. Used for both authoritative folder-name
    matching (exact, post-normalization) and inference substring search.
    """
    return _NORM_RE.sub("", s.lower())


@dataclasses.dataclass
class AircraftDB:
    canonical: list[str]
    cockpit: dict[str, str]              # canonical -> cockpit folder name
    _norm_external: dict[str, str]       # norm(name) -> canonical (curated)
    _norm_cockpit: dict[str, str]        # norm(cockpit folder) -> canonical
    _norm_recognized: dict[str, str]     # norm(datamine type) -> canonical (alias-applied)
    _tokens: list[tuple[str, str]]       # (norm token, canonical)

    def match_folder(self, folder: str) -> tuple[str, str] | None:
        """Authoritative match of a DCS aircraft folder name.

        Returns (canonical, dest_folder) where dest_folder is the canonical
        external folder or the canonical `Cockpit_<X>` folder. Curated
        (hosted) entries win; otherwise the broader datamine `recognized`
        set lets a not-yet-hosted airframe (e.g. C-130J-30) resolve so it
        can be bootstrapped. None if `folder` is not a recognized aircraft.
        """
        nf = _norm(folder)
        if nf in self._norm_external:
            c = self._norm_external[nf]
            return c, c
        if nf in self._norm_cockpit:
            c = self._norm_cockpit[nf]
            return c, self.cockpit[c]
        if nf in self._norm_recognized:
            c = self._norm_recognized[nf]
            return c, c
        # Generic `Cockpit_<X>` for a curated or recognized airframe.
        if folder.lower().startswith("cockpit_"):
            inner = _norm(folder[len("cockpit_"):])
            if inner in self._norm_external:
                c = self._norm_external[inner]
                return c, self.cockpit.get(c, f"Cockpit_{c}")
            if inner in self._norm_recognized:
                c = self._norm_recognized[inner]
                return c, f"Cockpit_{c}"
        return None

    def infer(self, signals: list[str]) -> set[str]:
        """Return the set of canonical aircraft any signal matches."""
        matched: set[str] = set()
        for tok, canonical in self._tokens:
            if tok and any(tok in s for s in signals):
                matched.add(canonical)
        return matched


def load_db(path: Path = DEFAULT_DB_PATH) -> AircraftDB:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    canonical: list[str] = []
    cockpit: dict[str, str] = {}
    norm_external: dict[str, str] = {}
    norm_cockpit: dict[str, str] = {}
    tokens: list[tuple[str, str]] = []
    for entry in data["aircraft"]:
        name = entry["name"]
        canonical.append(name)
        norm_external[_norm(name)] = name
        ck = entry.get("cockpit")
        if ck:
            cockpit[name] = ck
            norm_cockpit[_norm(ck)] = name
        for tok in entry.get("tokens", []):
            tokens.append((_norm(tok), name))
    # Broad recognition set from the DCS datamine. Each name maps to its
    # alias target (a hosted livery-dir) if one exists, else itself.
    aliases = data.get("aliases", {})
    norm_recognized: dict[str, str] = {}
    for name in data.get("recognized", []):
        norm_recognized.setdefault(_norm(name), aliases.get(name, name))
    return AircraftDB(
        canonical, cockpit, norm_external, norm_cockpit, norm_recognized, tokens
    )


@dataclasses.dataclass
class ResolvedLivery:
    aircraft: str       # canonical aircraft name
    dest_folder: str    # <Aircraft> or Cockpit_<Aircraft> (rsync dest)
    slug: str           # livery folder name
    zip_prefix: str     # prefix to strip when extracting this slug
    method: str         # how the aircraft was determined

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class LayoutResult:
    liveries: list[ResolvedLivery]
    aircraft: list[str]              # distinct canonical, sorted
    findings: list[Finding]

    def to_dict(self) -> dict:
        return {
            "liveries": [l.to_dict() for l in self.liveries],
            "aircraft": self.aircraft,
        }


def _slug_roots(names: list[str]) -> dict[str, str]:
    """Map each livery-slug root path to its description.lua entry name.

    A livery is identified by a `description.lua` at its root (the DCS
    convention). The root is everything above that file. Junk files at
    other levels (ReadMe.txt, stray images) never become slug roots, so
    they're simply ignored.
    """
    roots: dict[str, str] = {}
    for n in names:
        parts = n.split("/")
        if parts[-1].lower() == "description.lua" and len(parts) >= 2:
            root = "/".join(parts[:-1])
            roots.setdefault(root, n)
    return roots


def resolve(
    zf: zipfile.ZipFile,
    *,
    extra_signals: list[str] | None = None,
    db: AircraftDB | None = None,
) -> LayoutResult:
    db = db or load_db()
    extra_norm = [_norm(s) for s in (extra_signals or []) if s]

    names = [
        i.filename.replace("\\", "/")
        for i in zf.infolist()
        if not i.is_dir()
    ]
    roots = _slug_roots(names)
    findings: list[Finding] = []

    if not roots:
        findings.append(Finding(
            tier=LAYOUT_TIER, reason="layout_no_liveries",
            detail="no description.lua found -- not a DCS livery pack",
        ))
        return LayoutResult([], [], findings)

    liveries: list[ResolvedLivery] = []
    structural = 0
    bare = 0

    for root in sorted(roots):
        parts = root.split("/")
        slug = parts[-1]
        prefix = root + "/"
        resolved: ResolvedLivery | None = None

        # 1. Structural via a `Liveries/<Aircraft>/<slug>` path. Require
        #    Liveries to sit exactly two levels above the slug so that
        #    parts[li+1] is the aircraft folder and parts[li+2] is the
        #    slug (the last component). This holds whether or not there
        #    is a wrapper folder above Liveries/.
        if "Liveries" in parts:
            li = parts.index("Liveries")
            if li == len(parts) - 3:
                af = parts[li + 1]
                m = db.match_folder(af)
                if m:
                    canonical, dest = m
                    resolved = ResolvedLivery(
                        canonical, dest, slug, prefix, "structural_liveries")
                else:
                    findings.append(Finding(
                        tier=LAYOUT_TIER,
                        reason=f"layout_unknown_aircraft_folder:{af}",
                        detail=(
                            f"'{af}' under Liveries/ is not a recognized DCS "
                            f"aircraft folder (slug '{slug}')"),
                    ))
                    continue

        # 2. Structural via an aircraft-named parent folder
        #    (`<Aircraft>/<slug>/...`).
        if resolved is None and len(parts) >= 2:
            m = db.match_folder(parts[-2])
            if m:
                canonical, dest = m
                resolved = ResolvedLivery(
                    canonical, dest, slug, prefix, "structural_folder")

        # 3. Bare upload: infer from every available signal.
        if resolved is None:
            members = [n for n in names if n.startswith(prefix)]
            signals = [_norm(slug)]
            signals += [_norm(n.rsplit("/", 1)[-1]) for n in members]
            try:
                lua = zf.read(roots[root]).decode("utf-8", "replace")
                signals.append(_norm(lua))
            except Exception:  # noqa: BLE001 -- a read error just drops one signal
                pass
            signals += extra_norm

            matched = db.infer(signals)
            if len(matched) == 1:
                canonical = next(iter(matched))
                # Bare uploads always route to the external aircraft folder.
                # A bare *cockpit* livery would land as external (dest ==
                # canonical, not Cockpit_<canonical>) -- there's no reliable
                # signal to tell them apart, and bare cockpit uploads are
                # rare. Structural Cockpit_<X>/ uploads route correctly.
                resolved = ResolvedLivery(
                    canonical, canonical, slug, prefix, "inferred")
            elif not matched:
                findings.append(Finding(
                    tier=LAYOUT_TIER, reason="layout_unresolved_aircraft",
                    detail=(
                        f"slug '{slug}': no aircraft matched from its "
                        f"folder name, textures, or filename -- staff must "
                        f"route it manually"),
                ))
                continue
            else:
                findings.append(Finding(
                    tier=LAYOUT_TIER, reason="layout_ambiguous_aircraft",
                    detail=(
                        f"slug '{slug}': matched multiple aircraft "
                        f"{sorted(matched)} -- ambiguous, staff must route"),
                ))
                continue

        liveries.append(resolved)
        if resolved.method.startswith("structural"):
            structural += 1
        else:
            bare += 1

    # A single zip that mixes an authoritative Liveries/<X>/ layout with
    # bare slug folders at the root is malformed -- refuse to guess how
    # the two halves relate. Hard reject.
    if structural and bare:
        findings.append(Finding(
            tier=LAYOUT_TIER, reason="layout_mixed_shapes",
            detail=(
                f"zip mixes {structural} structurally-placed liveries with "
                f"{bare} bare slug folder(s); upload one shape at a time"),
        ))
        return LayoutResult([], [], findings)

    aircraft = sorted({l.aircraft for l in liveries})
    return LayoutResult(liveries, aircraft, findings)
