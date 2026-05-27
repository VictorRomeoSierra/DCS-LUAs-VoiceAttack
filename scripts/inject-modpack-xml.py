#!/usr/bin/env python3
"""Inject a minimal ModPack.xml into existing per-aircraft livery zips.

Why: OMM's "old-fashion" zip parser requires the zip's top-level folder
name to match the file name (e.g. F-16C_50.zip must contain F-16C_50/...).
Our per-aircraft zips wrap content with Liveries/ instead, so OMM
rejects them with "unknown or wrong Mod Pack architecture."

The modern OMM Mod Pack format provides an opt-in escape: a ModPack.xml
(or *.omp file) at the zip root with:

  <Open_Mod_Manager_Package>
    <install>Liveries</install>
  </Open_Mod_Manager_Package>

tells OMM "this is a Mod Pack; strip 'Liveries/' from entry paths before
installing." Entry paths then become <Aircraft>/<livery>/... and install
relative to the channel target. For the install to land in
<SavedGames>/DCS/Liveries/<Aircraft>/... the user's OMM channel target
must be <SavedGames>/DCS/Liveries/ (not <SavedGames>/DCS/).

This script:
  1. Appends ModPack.xml to each ~/public_html/Mods/Liveries/<Aircraft>.zip
     that doesn't already contain one.
  2. Recomputes bytes + xxhsum for modified zips.
  3. Re-emits the manifest with the new values.

Idempotent -- re-running on a zip that already has ModPack.xml skips it.

Optional arg: a single aircraft name to limit the operation (e.g. for
test-on-one-first workflow):

    python3 ~/bin/inject-modpack-xml.py            # all aircraft
    python3 ~/bin/inject-modpack-xml.py IL-76MD    # just IL-76MD
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
OUT_DIR = HOME / "public_html" / "Mods" / "Liveries"
MANIFEST = OUT_DIR / "manifest.json"

MODPACK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Open_Mod_Manager_Package>
  <install>Liveries</install>
</Open_Mod_Manager_Package>
"""


def xxhash_file(path):
    h = xxhash.xxh3_64()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    target_filter = sys.argv[1] if len(sys.argv) > 1 else None

    if not OUT_DIR.is_dir():
        sys.exit(f"missing {OUT_DIR}")

    # Load existing manifest (preserves built_at + aircraft entries that
    # might not get touched by this run).
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    else:
        manifest = {"aircraft": {}}
    aircraft_map = manifest.setdefault("aircraft", {})

    touched = 0
    skipped = 0
    for zip_path in sorted(OUT_DIR.glob("*.zip")):
        aircraft = zip_path.stem  # e.g. "IL-76MD"
        if target_filter and aircraft != target_filter:
            continue

        # Check if ModPack.xml already exists in the zip
        with zipfile.ZipFile(zip_path, "r") as z:
            already = "ModPack.xml" in z.namelist()

        if already:
            print(f"  {zip_path.name}: ModPack.xml already present, recomputing hash only")
        else:
            with zipfile.ZipFile(zip_path, "a") as z:
                z.writestr("ModPack.xml", MODPACK_XML)
            print(f"  {zip_path.name}: ModPack.xml injected")
            touched += 1

        bytes_ = zip_path.stat().st_size
        xxhsum = xxhash_file(zip_path)
        aircraft_map[aircraft] = {"bytes": bytes_, "xxhsum": xxhsum}
        print(f"    bytes={bytes_:,}  xxhsum={xxhsum}")
        if not already:
            skipped = skipped  # noop
        else:
            skipped += 1

    manifest["built_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {MANIFEST}")
    print(f"touched {touched} zip(s), {skipped} already had ModPack.xml")


if __name__ == "__main__":
    main()
