"""Build the OpenModMan repository XML for VRS mod packs.

Emits Release/repo.xml, which is meant to be deployed to
https://victorromeosierra.com/Mods/repo.xml so OMM clients can subscribe
and auto-detect updates.

Two kinds of pack feed into the manifest:

1.  **VRS_AutoStarts** -- hardcoded below. The published artifact lives
    on GitHub Releases; the URL is the source of truth, so we stream
    it to compute bytes + xxhsum on every build. Build/upload the
    artifact first, then run this against the published URL.

2.  **Per-aircraft livery sub-packs** -- discovered by walking
    `liveries-index/<aircraft>/pack.json`. Each pack.json carries the
    pre-computed bytes + xxhsum (the per-aircraft zips on vrs.com are
    too large to stream-hash on every build). The publish flow
    (Phase 2+) is responsible for keeping pack.json fresh; Phase 1
    populates it from a one-shot manifest emitted by the vrs.com
    build script. Recompute manually with:

        ssh vrs.com 'python3 -c "
        import xxhash, os, sys
        h = xxhash.xxh3_64()
        p = sys.argv[1]
        with open(p, \"rb\") as f:
            for chunk in iter(lambda: f.read(1<<20), b\"\"): h.update(chunk)
        print(h.hexdigest(), os.path.getsize(p))
        " /home/customdc/public_html/Mods/Liveries/<Aircraft>.zip'

The monolithic Liveries.zip is intentionally NOT listed in repo.xml --
OMM users get per-aircraft entries (delta updates); OvGME users keep
downloading the monolith by direct URL from vrs.com.

Usage:
    python scripts/build-repo.py
"""

from __future__ import annotations

import base64
import json
import sys
import zlib
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import xxhash
except ImportError:
    sys.exit("missing dependency: pip install xxhash")

REPO_ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = REPO_ROOT / "Release"
BRANDING_DIR = Path(__file__).resolve().parent / "branding"
LIVERIES_INDEX = REPO_ROOT / "liveries-index"

# Stable UUID for this repository, generated once - do not change.
REPO_UUID = "5e8b3f1a-c4f2-4a6b-9d0e-1d8a2b4c6e8f"

REPO_TITLE = "VRS DCS Mods"

# 128x128 JPEG used for all VRS-branded mod thumbnails.
VRS_THUMBNAIL = BRANDING_DIR / "VRS-Logo-128.jpg"

# Base URL where per-aircraft livery sub-packs are published.
LIVERIES_BASE_URL = "https://victorromeosierra.com/Mods/Liveries"

VRS_AUTOSTARTS_DESCRIPTION = """\
VRS quick-start macros for the airframes flown on the Victor Romeo Sierra
DCS server. Each Macro_sequencies.lua adds a consistent VRS Quick Start
sequence on the in-game autostart keybind, so you can spin up your aircraft
with a single press while playing on VRS.

Aircraft covered:
  - A-10C II
  - AH-64D
  - F/A-18C
  - Ka-50 III
  - Mi-24P
  - Mi-8MTV2
  - SA342 Gazelle
  - UH-1H Huey

Website: https://victorromeosierra.com
Source:  https://github.com/VictorRomeoSierra/VRSMods
"""

LIVERIES_DESCRIPTION_TEMPLATE = """\
VRS squadron and unit liveries for the {display_name}.

Drops aircraft-specific paint schemes into your DCS Saved Games\\Liveries
folder so other VRS pilots see your unit colors in the cockpit and
externally. OMM auto-updates this pack on next launch whenever new
liveries land.

Website: https://victorromeosierra.com
"""

VRS_AUTOSTARTS_PACK = {
    "ident": "VRS_AutoStarts_v1.0.0",
    "file": "VRS_AutoStarts.zip",
    "category": "VRS",
    "url": "https://github.com/VictorRomeoSierra/VRSMods/releases/latest/download/VRS_AutoStarts.zip",
    "description": VRS_AUTOSTARTS_DESCRIPTION,
    "thumbnail": VRS_THUMBNAIL,
    "channel": "install",  # installs at <DCS install root>/Mods/aircraft/...
}


def discover_aircraft_packs() -> list[dict]:
    """Walk liveries-index/ and yield one pack dict per aircraft.

    Each `liveries-index/<aircraft>/pack.json` looks like:

        {
          "aircraft": "FA-18C_hornet",
          "display_name": "F/A-18C Hornet",
          "bytes": 1234567890,
          "xxhsum": "abc123def456",
          "last_built_at": "2026-05-24T15:30:00Z"
        }
    """
    packs = []
    if not LIVERIES_INDEX.exists():
        return packs
    for aircraft_dir in sorted(LIVERIES_INDEX.iterdir()):
        if not aircraft_dir.is_dir():
            continue
        pack_json = aircraft_dir / "pack.json"
        if not pack_json.exists():
            continue
        data = json.loads(pack_json.read_text(encoding="utf-8"))
        aircraft = data["aircraft"]
        display_name = data.get("display_name", aircraft)
        if "bytes" not in data or "xxhsum" not in data:
            print(f"  skipping {aircraft}: pack.json missing bytes/xxhsum (placeholder?)")
            continue
        packs.append({
            "ident": f"Liveries_{aircraft}",
            "file": f"{aircraft}.zip",
            "category": "VRS Liveries",
            "url": f"{LIVERIES_BASE_URL}/{aircraft}.zip",
            "skip_fetch": True,
            "bytes": data["bytes"],
            "xxhsum": data["xxhsum"],
            "description": LIVERIES_DESCRIPTION_TEMPLATE.format(display_name=display_name),
            "thumbnail": VRS_THUMBNAIL,
            "channel": "savedgames",  # installs at <SavedGames>/DCS/Liveries/...
        })
    return packs


def hash_url(url: str) -> tuple[int, str]:
    h = xxhash.xxh3_64()
    size = 0
    req = Request(url, headers={"User-Agent": "build-repo.py"})
    with urlopen(req) as resp:
        if resp.status != 200:
            sys.exit(f"GET {url}: HTTP {resp.status}")
        for chunk in iter(lambda: resp.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return size, h.hexdigest()


def resolve_pack(pack: dict) -> dict:
    if pack.get("skip_fetch"):
        if "bytes" not in pack or "xxhsum" not in pack:
            sys.exit(f"{pack['ident']}: skip_fetch requires bytes+xxhsum")
        return pack
    print(f"  fetching {pack['url']} ...")
    size, xxhsum = hash_url(pack["url"])
    return {**pack, "bytes": size, "xxhsum": xxhsum}


def xml_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def thumbnail_datauri(path: Path) -> str:
    """Encode a JPEG image as a base64 DataURI matching what OMM expects."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def description_datauri(text: str) -> tuple[int, str]:
    """zlib-deflate UTF-8 text + base64-wrap as DataURI.

    Returns (uncompressed_byte_count, datauri). The byte count goes into
    the <description bytes="..."> attribute; OMM uses it to size the
    inflate buffer when it decodes our content.
    """
    utf8 = text.encode("utf-8")
    deflated = zlib.compress(utf8, level=9)
    b64 = base64.b64encode(deflated).decode("ascii")
    return len(utf8), f"data:application/octet-stream;base64,{b64}"


def build_xml(packs: list[dict]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<Open_Mod_Manager_Repository>",
        f"  <uuid>{REPO_UUID}</uuid>",
        f"  <title>{xml_escape(REPO_TITLE)}</title>",
        "  <downpath>files/</downpath>",
        f'  <references count="{len(packs)}">',
    ]
    for p in packs:
        attrs = (
            f'ident="{xml_escape(p["ident"])}" '
            f'file="{xml_escape(p["file"])}" '
            f'bytes="{p["bytes"]}" '
            f'xxhsum="{p["xxhsum"]}" '
            f'category="{xml_escape(p["category"])}"'
        )
        lines.append(f"    <mod {attrs}>")
        lines.append(f"      <url>{xml_escape(p['url'])}</url>")
        if "thumbnail" in p:
            thumb_path = Path(p["thumbnail"])
            if not thumb_path.exists():
                sys.exit(f"{p['ident']}: thumbnail not found: {thumb_path}")
            lines.append(f"      <thumbnail>{thumbnail_datauri(thumb_path)}</thumbnail>")
        if "description" in p:
            byte_count, uri = description_datauri(p["description"])
            lines.append(f'      <description bytes="{byte_count}">{uri}</description>')
        lines.append("    </mod>")
    lines.append("  </references>")
    lines.append("</Open_Mod_Manager_Repository>")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    packs = [VRS_AUTOSTARTS_PACK] + discover_aircraft_packs()
    resolved = [resolve_pack(p) for p in packs]

    # Two channel-specific manifests so the user can subscribe each OMM
    # channel to the matching install root, plus a combined manifest as
    # a backwards-compat URL for anyone still on the old subscription.
    # Deployment paths on vrs.com:
    #   VRSInstall.xml      -> public_html/VRSInstall.xml
    #   VRSSavedGames.xml   -> public_html/VRSSavedGames.xml
    #   repo.xml            -> public_html/Mods/repo.xml  (legacy combined URL)
    outputs = {
        "VRSInstall.xml":     [p for p in resolved if p.get("channel") == "install"],
        "VRSSavedGames.xml":  [p for p in resolved if p.get("channel") == "savedgames"],
        "repo.xml":           resolved,
    }
    for fname, subset in outputs.items():
        xml = build_xml(subset)
        out = RELEASE_DIR / fname
        out.write_text(xml, encoding="utf-8")
        print(f"wrote {out}  ({len(subset)} mods)")
    print()
    for p in resolved:
        print(f"  [{p.get('channel', '?'):>11s}] {p['ident']:40s} {p['bytes']:>12,} bytes  {p['xxhsum']}")


if __name__ == "__main__":
    main()
