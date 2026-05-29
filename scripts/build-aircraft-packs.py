#!/usr/bin/env python3
"""Repackage liveries into per-aircraft OMM sub-packs.

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

Two source modes:

  - **zip source** (`--source path/to/Liveries.zip`): reads from the
    monolithic zip the way Phase 1 did. Backwards-compat.

  - **dir source** (`--source path/to/livery-source/`): reads from a
    directory tree laid out as `<src_folder>/<slug>/<files>` where
    `<src_folder>` is the pre-RENAME folder name (e.g. `il-76md`, or
    `F-16C` to fold into F-16C_50). This is the Phase 2c+ shape --
    publish.py SSH-pushes new slugs into `~/livery-source/` on vrs.com
    and triggers this script to rebuild just the affected aircraft.

`--aircraft <name>` (may be repeated) restricts the build to one or
more aircraft. With `--aircraft`, manifest.json is **merged** into
rather than replaced -- entries for non-rebuilt aircraft are
preserved. Use this for the publish.py incremental rebuild flow.

Inline transforms applied while repackaging:
  - Case-fix renames (RENAME map: a-10c -> A-10C, etc.)
  - F-16C contents merged into F-16C_50 (user-confirmed)

Idempotent. Single pass per aircraft. Output uses ZIP_STORED (the
source already stores DDS content uncompressed; recompression would
waste CPU).

Usage:
    python3 build-aircraft-packs.py [--source <path>] [--out <dir>] [--aircraft <name>...]

Defaults target a vrs.com layout:
    --source $HOME/public_html/Mods/Liveries.zip
    --out    $HOME/public_html/Mods/Liveries

Incremental rebuild (Phase 2c publish.py invocation):
    python3.12 build-aircraft-packs.py \
        --source ~/livery-source \
        --out    ~/public_html/Mods/Liveries \
        --aircraft IL-76MD

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


def _collect_from_zip(src):
    """Index a monolithic Liveries.zip by top-level Liveries/<folder>/.

    Returns {src_folder: [(filename, is_dir, ref)]} where ref is the
    ZipInfo (read lazily via the reader closure in main).
    """
    by_folder = {}
    for e in src.infolist():
        parts = e.filename.split("/", 2)
        if len(parts) < 2 or parts[0] != "Liveries":
            continue
        src_folder = parts[1]
        by_folder.setdefault(src_folder, []).append(
            (e.filename, e.is_dir(), e)
        )
    return by_folder


def _collect_from_dir(source_dir):
    """Index a ~/livery-source/<folder>/<slug>/... tree.

    Synthesizes `Liveries/<folder>/<slug>/<rest>` filenames so the
    downstream build_zip logic is shared with the zip-source path.
    Returns {src_folder: [(filename, is_dir, ref)]} where ref is the
    Path on disk (read lazily by the reader closure).
    """
    by_folder = {}
    for src_folder_path in sorted(source_dir.iterdir()):
        if not src_folder_path.is_dir():
            continue
        src_folder = src_folder_path.name
        entries = []
        for path in sorted(src_folder_path.rglob("*")):
            rel = path.relative_to(src_folder_path).as_posix()
            synthetic = f"Liveries/{src_folder}/{rel}"
            if path.is_dir():
                entries.append((synthetic + "/", True, path))
            elif path.is_file():
                entries.append((synthetic, False, path))
        if entries:
            by_folder[src_folder] = entries
    return by_folder


def build_zip(by_folder, reader, aircraft, cockpit, out, incremental=False):
    """Write or extend one per-aircraft zip with the 2-layer wrapper.

    incremental=True and <out> already exists: open it in append mode and
    write only the entries not already present, instead of rebuilding the
    whole pack from scratch. This is the publish path -- a per-aircraft
    pack can be multiple GB, and on throttled shared hosting rewriting +
    re-reading all of it to add one small livery blows past the SSH
    timeout. Appending touches only the new slug's bytes plus a rewritten
    central directory; the caller still re-hashes the full file afterwards
    (OMM needs the whole-file xxhsum). NOTE: append-only, so a re-upload
    of an *existing* slug (same name, changed textures) is NOT updated --
    that needs a full rebuild (drop the zip first, or run without
    --aircraft).

    Returns the number of entries newly written.
    """
    seen = set()
    appending = False
    if out.exists() and incremental:
        with zipfile.ZipFile(out, "r") as existing:
            seen = set(existing.namelist())
        appending = True
    elif out.exists():
        out.unlink()

    to_write = []
    collisions = []
    for target in [aircraft] + ([cockpit] if cockpit else []):
        for src_folder in sources_for(target):
            for filename, is_dir, ref in by_folder.get(src_folder, []):
                # Inner path -- the install-relative path that ends up
                # inside Saved Games/DCS/ after OMM strips the outer wrapper.
                inner = filename.replace(
                    f"Liveries/{src_folder}/",
                    f"Liveries/{target}/",
                    1,
                )
                if inner == f"Liveries/{src_folder}":
                    inner = f"Liveries/{target}"
                # Outer wrapper -- file-name match so OMM's old-fashion
                # parser strips this layer and leaves the inner path as the
                # install-relative entry.
                new_name = f"{aircraft}/{inner}"
                entry = new_name.rstrip("/") + "/" if is_dir else new_name
                if entry in seen:
                    # Already in the (existing or in-progress) zip. For a
                    # full build a same-name from a different source folder
                    # is a real merge collision worth reporting; for an
                    # incremental append it just means "already published".
                    if src_folder != target and not appending:
                        collisions.append(f"{src_folder} -> {target}: {entry}")
                    continue
                seen.add(entry)
                to_write.append((entry, is_dir, ref))

    if to_write:
        mode = "a" if appending else "w"
        with zipfile.ZipFile(out, mode, zipfile.ZIP_STORED) as dst:
            for entry, is_dir, ref in to_write:
                dst.writestr(entry, b"" if is_dir else reader(ref))
        # Cheap integrity check (reads the central directory only): catch a
        # truncated/corrupt append before the caller hashes + publishes.
        with zipfile.ZipFile(out, "r") as check:
            check.namelist()

    if collisions:
        print(f"  COLLISIONS in {out.name} ({len(collisions)} skipped):")
        for c in collisions[:10]:
            print(f"    - {c}")
        if len(collisions) > 10:
            print(f"    ... and {len(collisions) - 10} more")
    return len(to_write)


def _build_all(by_folder, reader, out_dir, wanted_aircraft, incremental=False):
    """Build per-aircraft zips. wanted_aircraft=None means all 22."""
    if wanted_aircraft:
        known = dict(AIRCRAFT)
        aircraft_list = []
        for a in dict.fromkeys(wanted_aircraft):  # dedup, keep order
            if a in known:
                aircraft_list.append((a, known[a]))
            else:
                # A new airframe we don't host yet (the scanner recognized it
                # against the DCS datamine and publish.py is bootstrapping it).
                # Pair it with a generic Cockpit_<X>; that's a no-op when the
                # source carries no cockpit slugs.
                print(f"  note: '{a}' is a new airframe -- bootstrapping its pack")
                aircraft_list.append((a, f"Cockpit_{a}"))
    else:
        aircraft_list = AIRCRAFT

    results = {}
    for aircraft, cockpit in aircraft_list:
        out = out_dir / f"{aircraft}.zip"
        verb = "updating" if (incremental and out.exists()) else "building"
        print(f"{verb} {aircraft}.zip ...")
        n = build_zip(by_folder, reader, aircraft, cockpit, out, incremental=incremental)
        # Skip only when there's genuinely nothing to ship. In incremental
        # mode an existing non-empty zip with no new slugs (n == 0) is the
        # normal "nothing changed" case -- keep it and record its hash.
        if not out.exists() or out.stat().st_size == 0:
            print(f"  WARN: {aircraft}.zip would be empty -- skipping")
            if out.exists():
                out.unlink()
            continue
        bytes_ = out.stat().st_size
        xxhsum = xxhash_file(out)
        results[aircraft] = {"bytes": bytes_, "xxhsum": xxhsum}
        print(f"  -> +{n} new entries  {bytes_:>12,} bytes  {xxhsum}")
    return results


def _write_manifest(out_dir, results, incremental):
    """Write manifest.json. If incremental, merge results into existing."""
    manifest_path = out_dir / "manifest.json"
    if incremental and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        merged = dict(existing.get("aircraft", {}))
        merged.update(results)
        results = merged
    manifest = {
        "built_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "aircraft": results,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest_path


def main():
    home = Path.home()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=home / "public_html" / "Mods" / "Liveries.zip",
        help="Monolithic Liveries.zip OR ~/livery-source/ directory",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=home / "public_html" / "Mods" / "Liveries",
        help="Directory to write per-aircraft <Aircraft>.zip + manifest.json into",
    )
    parser.add_argument(
        "--aircraft",
        action="append",
        metavar="NAME",
        help="Restrict build to this aircraft (may be repeated). "
             "manifest.json is merged rather than replaced.",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    if args.source.is_file() and args.source.suffix.lower() == ".zip":
        print(f"opening zip source: {args.source}")
        with zipfile.ZipFile(args.source, "r") as src:
            print(f"  {len(src.infolist()):,} entries in source")
            by_folder = _collect_from_zip(src)
            print(f"  {len(by_folder)} top-level folders\n")
            reader = src.read
            results = _build_all(by_folder, reader, args.out, args.aircraft)
    elif args.source.is_dir():
        print(f"reading dir source: {args.source}")
        by_folder = _collect_from_dir(args.source)
        print(f"  {len(by_folder)} top-level folders\n")
        reader = lambda ref: ref.read_bytes()
        # The targeted publish flow (--aircraft on a dir source) appends new
        # slugs to the existing per-aircraft pack instead of rebuilding the
        # whole multi-GB zip. A full dir rebuild (no --aircraft) stays a
        # from-scratch build so removed/renamed slugs are reflected.
        results = _build_all(
            by_folder, reader, args.out, args.aircraft,
            incremental=bool(args.aircraft),
        )
    else:
        sys.exit(f"--source not found or not a zip/dir: {args.source}")

    manifest_path = _write_manifest(
        args.out, results, incremental=bool(args.aircraft)
    )
    print(f"\nwrote {manifest_path}")


if __name__ == "__main__":
    main()
