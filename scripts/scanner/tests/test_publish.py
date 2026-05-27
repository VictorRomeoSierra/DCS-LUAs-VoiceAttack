"""Layout parsing + extraction tests for publish.py.

publish.py needs to recognize two zip shapes:

  - **Single-livery upload** (ProjectSend production path):
        <Aircraft>/<slug>/description.lua
        <Aircraft>/<slug>/*.dds

  - **Full-pack** (the test corpus shape, also what the user might
    upload by mistake):
        <Aircraft>/Liveries/<Aircraft>/<slug>/...
        <Aircraft>/Liveries/Cockpit_<Aircraft>/<slug>/...

Both must yield the right (aircraft, slugs) tuple and extract slug
content with the zip-prefix stripped.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.scanner.publish import _parse_layout, _extract_slug


def _build(zip_path: Path, files: dict[str, bytes]) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return zip_path


def test_single_livery_layout(tmp_path):
    zp = _build(tmp_path / "single.zip", {
        "FA-18C_hornet/VRS-001/description.lua": b"livery = {}\n",
        "FA-18C_hornet/VRS-001/tex.dds": b"DDS \0\0\0\0",
    })
    aircraft, slugs = _parse_layout(zp)
    assert aircraft == "FA-18C_hornet"
    assert slugs == [("FA-18C_hornet", "VRS-001", "FA-18C_hornet/VRS-001/")]


def test_full_pack_layout_external_only(tmp_path):
    zp = _build(tmp_path / "fullpack-ext.zip", {
        "IL-76MD/Liveries/IL-76MD/MD USSR/description.lua": b"livery = {}\n",
        "IL-76MD/Liveries/IL-76MD/MD USSR/tex.dds": b"DDS \0\0\0\0",
    })
    aircraft, slugs = _parse_layout(zp)
    assert aircraft == "IL-76MD"
    assert slugs == [("IL-76MD", "MD USSR", "IL-76MD/Liveries/IL-76MD/MD USSR/")]


def test_full_pack_layout_with_cockpit(tmp_path):
    """Mi-8MT has both external + cockpit liveries; both must surface."""
    zp = _build(tmp_path / "fullpack-mix.zip", {
        "Mi-8MT/Liveries/Mi-8MT/Skin-A/description.lua": b"livery={}\n",
        "Mi-8MT/Liveries/Cockpit_Mi-8MT/Cockpit-A/description.lua": b"livery={}\n",
    })
    aircraft, slugs = _parse_layout(zp)
    assert aircraft == "Mi-8MT"
    assert sorted(slugs) == [
        ("Cockpit_Mi-8MT", "Cockpit-A", "Mi-8MT/Liveries/Cockpit_Mi-8MT/Cockpit-A/"),
        ("Mi-8MT", "Skin-A", "Mi-8MT/Liveries/Mi-8MT/Skin-A/"),
    ]


def test_multiple_slugs_dedup(tmp_path):
    """Two files in the same slug folder shouldn't yield two slug entries."""
    zp = _build(tmp_path / "dup.zip", {
        "A-10C_2/Skin-1/description.lua": b"livery={}\n",
        "A-10C_2/Skin-1/tex.dds": b"DDS \0\0\0\0",
        "A-10C_2/Skin-2/description.lua": b"livery={}\n",
    })
    aircraft, slugs = _parse_layout(zp)
    assert aircraft == "A-10C_2"
    assert sorted(slug for _, slug, _ in slugs) == ["Skin-1", "Skin-2"]


def test_multiple_top_folders_rejected(tmp_path):
    """A zip with two top folders is malformed for our pipeline."""
    zp = _build(tmp_path / "two-tops.zip", {
        "FA-18C_hornet/Skin/description.lua": b"livery={}\n",
        "F-16C_50/Other/description.lua": b"livery={}\n",
    })
    try:
        _parse_layout(zp)
    except ValueError as e:
        assert "one top folder" in str(e)
    else:
        raise AssertionError("expected ValueError on multi-top zip")


def test_extract_slug_strips_prefix(tmp_path):
    zp = _build(tmp_path / "ext.zip", {
        "IL-76MD/Liveries/IL-76MD/MD USSR/description.lua": b"hello\n",
        "IL-76MD/Liveries/IL-76MD/MD USSR/sub/tex.dds": b"DDS\0",
    })
    out = tmp_path / "extracted"
    n = _extract_slug(
        zp,
        ("IL-76MD", "MD USSR", "IL-76MD/Liveries/IL-76MD/MD USSR/"),
        out,
    )
    assert n == 2
    assert (out / "MD USSR" / "description.lua").read_bytes() == b"hello\n"
    assert (out / "MD USSR" / "sub" / "tex.dds").read_bytes() == b"DDS\0"


def test_extract_slug_skips_traversal(tmp_path):
    """Defense-in-depth: even if a `..` slipped past the scanner, the
    extractor must skip it."""
    zp = _build(tmp_path / "traverse.zip", {
        "FA-18C_hornet/Skin/../etc/passwd": b"r00t\n",
        "FA-18C_hornet/Skin/legit.dds": b"DDS\0",
    })
    out = tmp_path / "extracted"
    _extract_slug(
        zp,
        ("FA-18C_hornet", "Skin", "FA-18C_hornet/Skin/"),
        out,
    )
    # legit file landed; traversal entry was dropped
    assert (out / "Skin" / "legit.dds").exists()
    assert not list(out.parent.glob("**/passwd"))
