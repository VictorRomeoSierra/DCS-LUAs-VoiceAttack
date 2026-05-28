"""publish.py unit tests.

publish.py no longer parses zip layout itself -- the scanner
(layout.resolve) is the source of truth and stashes the result in
verdict["layout"]. These tests cover what publish.py still owns:

  - reading the resolved layout out of the verdict
  - extracting a slug's content with the zip-prefix stripped
  - locating a preview image in the staged content
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.scanner.publish import (
    _extract_slug,
    _find_preview,
    _layout_from_verdict,
)


def _build(zip_path: Path, files: dict[str, bytes]) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return zip_path


# ----- layout from verdict -------------------------------------------


def test_layout_from_verdict_multi_aircraft():
    verdict = {"layout": {
        "aircraft": ["Mi-24P", "Mi-8MT"],
        "liveries": [
            {"aircraft": "Mi-24P", "dest_folder": "Mi-24P",
             "slug": "Loco", "zip_prefix": "Liveries/Mi-24P/Loco/",
             "method": "structural_liveries"},
            {"aircraft": "Mi-8MT", "dest_folder": "Mi-8MT",
             "slug": "ShortBus", "zip_prefix": "Liveries/mi-8mt/ShortBus/",
             "method": "structural_liveries"},
        ],
    }}
    aircraft, slugs = _layout_from_verdict(verdict)
    assert aircraft == ["Mi-24P", "Mi-8MT"]
    assert slugs == [
        ("Mi-24P", "Loco", "Liveries/Mi-24P/Loco/"),
        ("Mi-8MT", "ShortBus", "Liveries/mi-8mt/ShortBus/"),
    ]


def test_layout_from_verdict_missing_raises():
    for verdict in ({}, {"layout": None}, {"layout": {"liveries": []}}):
        with pytest.raises(ValueError):
            _layout_from_verdict(verdict)


# ----- extraction ----------------------------------------------------


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
    assert (out / "Skin" / "legit.dds").exists()
    assert not list(out.parent.glob("**/passwd"))


# ----- preview discovery ---------------------------------------------


def test_find_preview_matches_preview_stem(tmp_path):
    root = tmp_path / "stage"
    (root / "FA-18C_hornet" / "Skin").mkdir(parents=True)
    (root / "FA-18C_hornet" / "Skin" / "preview.jpg").write_bytes(b"JPG")
    (root / "FA-18C_hornet" / "Skin" / "F18C_1.dds").write_bytes(b"DDS\0")
    found = _find_preview(root)
    assert found is not None and found.name == "preview.jpg"


def test_find_preview_ignores_non_preview_images(tmp_path):
    root = tmp_path / "stage"
    (root / "Skin").mkdir(parents=True)
    (root / "Skin" / "screenshot.png").write_bytes(b"PNG")
    assert _find_preview(root) is None
