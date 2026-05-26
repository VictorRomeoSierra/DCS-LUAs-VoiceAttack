#!/usr/bin/env python3
"""Repackage the monolithic Liveries.zip into per-aircraft sub-packs.

Reads from ~/public_html/Mods/Liveries.zip and writes per-aircraft zips
plus a manifest of bytes + xxhsum:

  - ~/public_html/Mods/Liveries/<Aircraft>.zip       (one per aircraft)
  - ~/public_html/Mods/Liveries/manifest.json        (bytes + xxhsum per pack)

Single zip-to-zip pass -- no filesystem extraction step in between, which
matters on cPanel hosts where inode-creation overhead for ~3000 small
files dominates real I/O cost. Applies the case-fix renames and the
F-16C -> F-16C_50 merge inline (RENAME map below).

Idempotent -- safe to re-run; rebuilds all zips and overwrites the manifest.

Output zips use ZIP_STORED (no recompression). The source is already
storing DDS/PNG/JPG content uncompressed in the monolithic zip, so
recompressing in the per-aircraft zips would waste CPU for ~zero size
savings. Forward-slash entries and explicit directory entries are
preserved so OvGME ingests them cleanly.

Run on vrs.com:
    python3 ~/bin/build-aircraft-packs.py

Required: python3 (3.6+) + xxhash. xxhash is the same dependency the
local build-repo.py uses; known available on vrs.com.
"""

import datetime
import json
import sys
import zipfile
from pathlib import Path

try:
    import xxhash
except ImportError:
    sys.exit("missing dependency: pip3 install --user xxhash")

HOME = Path.home()
SOURCE_ZIP = HOME / "public_html" / "Mods" / "Liveries.zip"
OUT_DIR = HOME / "public_html" / "Mods" / "Liveries"
MANIFEST = OUT_DIR / "manifest.json"

# Source folder name -> Target folder name (after case-fix and merge).
# Folders not in this map are passed through unchanged.
# F-16C -> F-16C_50 is the one content merge (user-confirmed: DCS-current
# uses F-16C_50 exclusively, so the legacy F-16C folder gets folded in).
RENAME = {
    "a-10c":            "A-10C",
    "a-10cII":          "A-10C_2",
    "Cockpit-Ka-50_3":  "Cockpit_Ka-50_3",
    "f-14b":            "F-14B",
    "il-76md":          "IL-76MD",
    "ka-50":            "Ka-50",
    "uh-60a":           "UH-60A",
    "Uh-1H":            "UH-1H",
    "F-16C":            "F-16C_50",
}

# Per-aircraft sub-pack: (target external folder, target cockpit folder or None).
# Cockpit-only sub-packs (AH-64D, Su-25T) carry no external content today.
AIRCRAFT = [
    ("A-10A",          None),
    ("A-10C",          None),
    ("A-10C_2",        None),
    ("A-4E-C",         None),
    ("AH-64D",         "Cockpit_AH-64D"),
    ("AV8BNA",         None),
    ("CH-47F",         None),
    ("F-14B",          None),
    ("F-16C_50",       None),
    ("FA-18C_hornet",  None),
    ("IL-76MD",        None),
    ("Ka-50",          None),
    ("Ka-50_3",        "Cockpit_Ka-50_3"),
    ("M-2000C",        None),
    ("Mi-24P",         "Cockpit_Mi-24P"),
    ("Mi-8MT",         "Cockpit_Mi-8MT"),
    ("MiG-21bis",      "Cockpit_MiG-21bis"),
    ("Su-25T",         "Cockpit_Su-25T"),
    ("Su-33",          "Cockpit_Su-33"),
    ("UH-1H",          "Cockpit_UH-1H"),
    ("UH-60A",         None),
    ("UH-60L",         None),
]


def sources_for(target):
    """Return the source folder names that map to a given target.

    A target may have multiple sources (the F-16C/F-16C_50 merge). It always
    includes itself unless it appears as a value in RENAME for some OTHER
    source -- in that case, only the explicit renames contribute.
    """
    sources = [src for src, dst in RENAME.items() if dst == target]
    # Also include target as identity if no rename targets it from a different name.
    if target not in RENAME:
        sources = [target] + sources
    return sources


def xxhash_file(path):
    h = xxhash.xxh3_64()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not SOURCE_ZIP.is_file():
        sys.exit(f"missing {SOURCE_ZIP}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"opening {SOURCE_ZIP} ...")
    with zipfile.ZipFile(SOURCE_ZIP, "r") as src:
        entries = src.infolist()
        print(f"  {len(entries):,} entries in source zip")

        # Index entries by their top-level folder (Liveries/<Folder>/...).
        by_folder = {}
        for e in entries:
            parts = e.filename.split("/", 2)
            if len(parts) < 2 or parts[0] != "Liveries":
                continue
            by_folder.setdefault(parts[1], []).append(e)
        print(f"  {len(by_folder)} top-level folders")

        results = {}
        for aircraft, cockpit in AIRCRAFT:
            out = OUT_DIR / f"{aircraft}.zip"
            if out.exists():
                out.unlink()

            total_entries = 0
            collisions = []
            seen = set()
            with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as dst:
                for target in [aircraft] + ([cockpit] if cockpit else []):
                    for src_folder in sources_for(target):
                        for e in by_folder.get(src_folder, []):
                            # Rewrite arcname: swap the source folder name for the target
                            # in the Liveries/<Folder>/... prefix.
                            new_name = e.filename.replace(
                                f"Liveries/{src_folder}/",
                                f"Liveries/{target}/",
                                1,
                            )
                            # Also handle the bare-folder entry "Liveries/<src_folder>/"
                            if new_name == f"Liveries/{src_folder}":
                                new_name = f"Liveries/{target}"
                            # Dedupe -- when merging F-16C into F-16C_50, the target's
                            # own entries are written first (target is index 0 in
                            # sources_for), so on collision the F-16C_50 version wins
                            # and the F-16C version is skipped + reported.
                            if new_name in seen:
                                if src_folder != target:
                                    collisions.append(f"{src_folder} -> {target}: {new_name}")
                                continue
                            seen.add(new_name)
                            data = src.read(e)
                            if e.is_dir():
                                dst.writestr(new_name.rstrip("/") + "/", b"")
                            else:
                                dst.writestr(new_name, data)
                            total_entries += 1
            if collisions:
                print(f"  COLLISIONS in {aircraft}.zip ({len(collisions)} skipped):")
                for c in collisions[:10]:
                    print(f"    - {c}")
                if len(collisions) > 10:
                    print(f"    ... and {len(collisions) - 10} more")

            if total_entries == 0:
                print(f"  WARN: {aircraft}.zip would be empty -- skipping")
                out.unlink()
                continue

            bytes_ = out.stat().st_size
            xxhsum = xxhash_file(out)
            results[aircraft] = {"bytes": bytes_, "xxhsum": xxhsum}
            print(f"  {aircraft}.zip: {total_entries:>5} entries  {bytes_:>12,} bytes  {xxhsum}")

    manifest = {
        "built_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aircraft": results,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {MANIFEST}")


if __name__ == "__main__":
    main()
