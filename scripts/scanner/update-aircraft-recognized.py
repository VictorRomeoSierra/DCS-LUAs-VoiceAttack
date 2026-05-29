#!/usr/bin/env python3
"""Refresh aircraft.json's `recognized` list from the DCS datamine.

The scanner's layout resolver needs to know which `Liveries/<X>/` folder
names are real DCS aircraft (so a new airframe we don't host yet -- e.g.
C-130J-30 -- is recognized and bootstrapped instead of rejected). Rather
than hand-maintaining that list, pull every plane + helicopter unit-type
name from Quaggles' DCS lua datamine, which dumps the full in-game unit
database every Open Beta patch.

This writes the snapshot into aircraft.json's `recognized` field; the
script is the source-of-truth pointer, the JSON is the committed snapshot.
Re-run when DCS adds airframes. The curated `aircraft` entries (with
inference tokens) and `aliases` are preserved untouched.

Usage:
    python scripts/scanner/update-aircraft-recognized.py
    # set GITHUB_TOKEN to avoid the 60 req/hr anonymous rate limit
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = "Quaggles/dcs-lua-datamine"
DIRS = (
    "_G/db/Units/Planes/Plane",
    "_G/db/Units/Helicopters/Helicopter",
)
AIRCRAFT_JSON = Path(__file__).resolve().parent / "aircraft.json"


def _api(path: str) -> list[dict]:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {
        "User-Agent": "vrs-aircraft-recognizer",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_type_names() -> list[str]:
    names: set[str] = set()
    for d in DIRS:
        for entry in _api(d):
            if entry.get("type") == "file" and entry["name"].endswith(".lua"):
                names.add(entry["name"][:-len(".lua")])
    return sorted(names)


def main() -> int:
    data = json.loads(AIRCRAFT_JSON.read_text(encoding="utf-8"))
    names = fetch_type_names()
    if not names:
        print("error: datamine returned no aircraft type names", file=sys.stderr)
        return 1
    data["recognized"] = names
    AIRCRAFT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(names)} recognized aircraft type names to "
          f"{AIRCRAFT_JSON.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
