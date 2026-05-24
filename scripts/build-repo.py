"""Build the OpenModMan repository XML for VRS mod packs.

Emits Release/repo.xml, which is meant to be deployed to
https://victorromeosierra.com/Mods/repo.xml so OMM clients can subscribe
and auto-detect updates.

The URL is the source of truth: this script streams from the URL to compute
the hash and size. That way, repo.xml always describes exactly what players
will download. Build/upload the artifact first, then run this against the
published URL.

For files we cannot fetch (e.g. the 9.7GB Liveries pack - too big to stream
on every build) you can supply pre-computed `bytes` and `xxhsum` and set
`skip_fetch: True`. Recompute those manually whenever the file changes:

    ssh vrs.com 'python3 -c "
    import xxhash, os
    h = xxhash.xxh3_64()
    p = \"/home/customdc/public_html/Mods/Liveries.zip\"
    with open(p, \"rb\") as f:
        for chunk in iter(lambda: f.read(1<<20), b\"\"): h.update(chunk)
    print(h.hexdigest(), os.path.getsize(p))
    "'

Usage:
    python scripts/build-repo.py
"""

from __future__ import annotations

import base64
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

# Stable UUID for this repository, generated once - do not change.
REPO_UUID = "5e8b3f1a-c4f2-4a6b-9d0e-1d8a2b4c6e8f"

REPO_TITLE = "VRS DCS Mods"

# 128x128 JPEG used for all VRS-branded mod thumbnails.
VRS_THUMBNAIL = BRANDING_DIR / "VRS-Logo-128.jpg"

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

VRS_LIVERIES_DESCRIPTION = """\
VRS squadron and unit liveries for the airframes flown on the Victor Romeo
Sierra DCS server. Drops aircraft-specific paint schemes into your DCS
Saved Games\\Liveries folder so other VRS pilots see your unit colors in
the cockpit and externally.

Note: this pack is 9.7 GB - allow time for the initial download.

Website: https://victorromeosierra.com
"""

PACKS = [
    {
        "ident": "VRS_AutoStarts_v1.0.0",
        "file": "VRS_AutoStarts.zip",
        "category": "VRS",
        "url": "https://github.com/VictorRomeoSierra/VRSMods/releases/latest/download/VRS_AutoStarts.zip",
        "description": VRS_AUTOSTARTS_DESCRIPTION,
        "thumbnail": VRS_THUMBNAIL,
    },
    {
        "ident": "Liveries_v1.0.0",
        "file": "Liveries.zip",
        "category": "VRS",
        "url": "https://victorromeosierra.com/Mods/Liveries.zip",
        "skip_fetch": True,
        "bytes": 9726122047,
        "xxhsum": "8973e4aa9f22d42c",
        "description": VRS_LIVERIES_DESCRIPTION,
        "thumbnail": VRS_THUMBNAIL,
    },
]


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
    resolved = [resolve_pack(p) for p in PACKS]
    xml = build_xml(resolved)
    out = RELEASE_DIR / "repo.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"wrote {out}")
    for p in resolved:
        print(f"  {p['ident']:30s} {p['bytes']:>12,} bytes  {p['xxhsum']}")


if __name__ == "__main__":
    main()
