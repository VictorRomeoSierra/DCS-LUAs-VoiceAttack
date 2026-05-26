#!/usr/bin/env python3
"""Update liveries-index/<aircraft>/pack.json from a manifest.

The manifest is produced by build-aircraft-packs.py on vrs.com and pulled
back via scp. It carries pre-computed bytes + xxhsum + built_at for every
sub-pack rebuilt in this batch. This script merges those values into the
per-aircraft pack.json files in the repo so the next `build-repo.py` run
picks them up.

Usage:
    python scripts/update-pack-index.py <manifest.json>

For Phase 1 manual:
    scp vrs.com:public_html/Mods/Liveries/manifest.json /tmp/m.json
    python scripts/update-pack-index.py /tmp/m.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVERIES_INDEX = REPO_ROOT / "liveries-index"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: update-pack-index.py <manifest.json>")
    manifest_path = Path(sys.argv[1])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    built_at = manifest.get("built_at")
    aircraft = manifest.get("aircraft", {})
    if not aircraft:
        sys.exit("manifest has no aircraft entries")

    updated = 0
    missing_dir = []
    for name, info in aircraft.items():
        d = LIVERIES_INDEX / name
        if not d.is_dir():
            missing_dir.append(name)
            continue
        pack_json = d / "pack.json"
        existing = json.loads(pack_json.read_text(encoding="utf-8")) if pack_json.exists() else {}
        existing["aircraft"] = name
        existing.setdefault("display_name", name)
        existing["bytes"] = info["bytes"]
        existing["xxhsum"] = info["xxhsum"]
        if built_at:
            existing["last_built_at"] = built_at
        pack_json.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        updated += 1
        print(f"  updated {pack_json.relative_to(REPO_ROOT)}: {info['bytes']:>12,} bytes  {info['xxhsum']}")

    if missing_dir:
        print(f"\nWARN: manifest had aircraft with no liveries-index/ dir:", file=sys.stderr)
        for n in missing_dir:
            print(f"  - {n}", file=sys.stderr)

    print(f"\n{updated} pack.json files updated from {manifest_path}")


if __name__ == "__main__":
    main()
