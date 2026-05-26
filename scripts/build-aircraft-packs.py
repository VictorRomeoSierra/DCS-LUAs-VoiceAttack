#!/usr/bin/env python3
"""Repackage the monolithic Liveries.zip into per-aircraft sub-packs.

Each output zip is structured to match the OvGME / OMM old-fashion
convention: a single outer folder whose name matches the file's stem,
containing the actual install tree. For a livery pack this means:

    <Aircraft>.zip
      <Aircraft>/                   <- outer wrapper, file-name match
        Liveries/
          <Aircraft>/                <- DCS aircraft folder name
            <livery-name>/
              description.lua
              *.dds
          Cockpit_<Aircraft>/        <- if the aircraft has cockpit liveries
            <livery-name>/
              ...

When OMM (or OvGME) extracts the pack into a generic channel target
(e.g. <SavedGames>/DCS/), the outer wrapper is stripped and the
remaining `Liveries/<Aircraft>/...` path lands in the right place
under the user's Saved Games. No ModPack.xml is needed -- OMM's
default file-name = top-folder parser handles it.

Inline transforms applied while repackaging:
  - Case-fix renames (RENAME map: a-10c -> A-10C, etc.)
  - F-16C contents merged into F-16C_50 (user-confirmed)

Idempotent. Single zip-to-zip pass -- no filesystem extraction.
Output uses ZIP_STORED (the source already stores DDS content
uncompressed; recompression would waste CPU).

Usage:
    python3 build-aircraft-packs.py [--source <path>] [--out <dir>]

Defaults target a vrs.com layout:
    --source $HOME/public_html/Mods/Liveries.zip
    --out    $HOME/public_html/Mods/Liveries

For a local rebuild on the user's workstation:
    python build-aircraft-packs.py \
        --source ~/Downloads/Liveries.zip \
        --out Release/aircraft-packs

Required: python3 + xxhash. On vrs.com the default python3 is 3.6 and
fails to open the 9 GB Zip64 source, so use python3.12 (which needed
pip + xxhash bootstrapped via get-pip.py).
"""

import argparse
import datetime
import json
import sys
import zipfile
from pathlib import Path

try:
    import xxhash
except ImportError:
    sys.exit("missing dependency: pip3 install --user xxhash")

# Source folder name -> Target folder name (after case-fix and merge).
# Folders not in this map are passed through unchanged. F-16C contents
# get merged into F-16C_50 (user-confirmed: DCS-current uses F-16C_50
# exclusively, so the legacy F-16C folder gets folded in).
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

# (target external folder, target cockpit folder or None).
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
    """Source folder names that map to a given target.

    A target may have multiple sources (the F-16C/F-16C_50 merge). It
    includes itself unless it's only ever the destination of a rename.
    """
    sources = [src for src, dst in RENAME.items() if dst == target]
    if target not in RENAME:
        sources = [target] + sources
    return sources


def xxhash_file(path):
    h = xxhash.xxh3_64()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_zip(src, by_folder, aircraft, cockpit, out):
    """Write one per-aircraft zip with the 2-layer wrapper structure."""
    if out.exists():
        out.unlink()

    total_entries = 0
    collisions = []
    seen = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as dst:
        for target in [aircraft] + ([cockpit] if cockpit else []):
            for src_folder in sources_for(target):
                for e in by_folder.get(src_folder, []):
                    # Inner path -- the install-relative path that ends
                    # up inside Saved Games/DCS/ after OMM strips the
                    # outer wrapper.
                    inner = e.filename.replace(
                        f"Liveries/{src_folder}/",
                        f"Liveries/{target}/",
                        1,
                    )
                    if inner == f"Liveries/{src_folder}":
                        inner = f"Liveries/{target}"
                    # Outer wrapper -- file-name match so OMM's
                    # old-fashion parser strips this layer and leaves
                    # the inner path as the install-relative entry.
                    new_name = f"{aircraft}/{inner}"
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
        print(f"  COLLISIONS in {out.name} ({len(collisions)} skipped):")
        for c in collisions[:10]:
            print(f"    - {c}")
        if len(collisions) > 10:
            print(f"    ... and {len(collisions) - 10} more")
    return total_entries


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=home / "public_html" / "Mods" / "Liveries.zip",
        help="Monolithic Liveries.zip to read from",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=home / "public_html" / "Mods" / "Liveries",
        help="Directory to write per-aircraft <Aircraft>.zip + manifest.json into",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        sys.exit(f"missing source zip: {args.source}")
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"opening {args.source} ...")
    with zipfile.ZipFile(args.source, "r") as src:
        entries = src.infolist()
        print(f"  {len(entries):,} entries in source zip")

        by_folder = {}
        for e in entries:
            parts = e.filename.split("/", 2)
            if len(parts) < 2 or parts[0] != "Liveries":
                continue
            by_folder.setdefault(parts[1], []).append(e)
        print(f"  {len(by_folder)} top-level folders\n")

        results = {}
        for aircraft, cockpit in AIRCRAFT:
            out = args.out / f"{aircraft}.zip"
            print(f"building {aircraft}.zip ...")
            n = build_zip(src, by_folder, aircraft, cockpit, out)
            if n == 0:
                print(f"  WARN: {aircraft}.zip would be empty -- skipping")
                if out.exists():
                    out.unlink()
                continue
            bytes_ = out.stat().st_size
            xxhsum = xxhash_file(out)
            results[aircraft] = {"bytes": bytes_, "xxhsum": xxhsum}
            print(f"  -> {n:>5} entries  {bytes_:>12,} bytes  {xxhsum}")

    manifest_path = args.out / "manifest.json"
    manifest = {
        "built_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "aircraft": results,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {manifest_path}")


if __name__ == "__main__":
    main()
