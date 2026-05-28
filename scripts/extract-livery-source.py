#!/usr/bin/env python3
"""One-shot migration: extract Liveries.zip into ~/livery-source/.

The resulting tree is the source-of-truth for the Phase 2c+ rebuild
flow. After this runs, build-aircraft-packs.py can be invoked with
`--source ~/livery-source` to rebuild per-aircraft zips. publish.py
SSH-pushes new livery slugs into this tree and triggers an
incremental rebuild.

Layout after extraction:

    ~/livery-source/
      <src_folder>/                  # pre-RENAME folder name
        <slug>/                      # livery folder
          description.lua
          *.dds
          ...

The RENAME map in build-aircraft-packs.py is applied at zip-time, so
src_folder names like `il-76md` and `F-16C` stay as-is here but end
up rewritten inside the published zips.

Run once on vrs.com:

    python3.12 ~/bin/extract-livery-source.py

Disk: extracting the current 9.7 GB monolith produces ~25 GB on disk
(uncompressed; DDS textures dominate). Check `df -h ~` first.
"""

import argparse
import sys
import zipfile
from pathlib import Path

DEFAULT_SOURCE = Path.home() / "public_html" / "Mods" / "Liveries.zip"
DEFAULT_OUT = Path.home() / "livery-source"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be written; don't touch disk."
    )
    args = parser.parse_args()

    if not args.source.is_file():
        sys.exit(f"source not found: {args.source}")
    if args.out.exists() and any(args.out.iterdir()):
        sys.exit(
            f"refusing to extract into non-empty directory: {args.out}\n"
            f"if intentional, mv it aside first."
        )
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"opening {args.source} ...")
    written = 0
    skipped = 0
    bytes_ = 0
    with zipfile.ZipFile(args.source, "r") as src:
        entries = src.infolist()
        print(f"  {len(entries):,} entries in source")
        for e in entries:
            name = e.filename
            if not name.startswith("Liveries/"):
                skipped += 1
                continue
            rel = name[len("Liveries/"):]
            if not rel or rel.endswith("/"):
                continue
            if ".." in rel.split("/"):
                skipped += 1
                continue
            out_path = args.out / rel
            if args.dry_run:
                if written < 5:
                    print(f"  would write {out_path}")
                written += 1
                continue
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with src.open(e) as fsrc, open(out_path, "wb") as fdst:
                while True:
                    chunk = fsrc.read(1 << 20)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    bytes_ += len(chunk)
            written += 1
            if written % 1000 == 0:
                print(f"  ...{written:,} files ({bytes_ / 1024**3:.2f} GiB)")
    print(
        f"done. wrote {written:,} files ({bytes_ / 1024**3:.2f} GiB), "
        f"skipped {skipped}."
    )


if __name__ == "__main__":
    main()
