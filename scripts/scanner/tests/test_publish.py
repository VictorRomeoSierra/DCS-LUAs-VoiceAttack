"""publish.py unit tests.

publish.py no longer parses zip layout itself -- the scanner
(layout.resolve) is the source of truth and stashes the result in
verdict["layout"]. These tests cover what publish.py still owns:

  - reading the resolved layout out of the verdict
  - extracting a slug's content with the zip-prefix stripped
  - locating a preview image in the staged content
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

import json as _json

from scripts.scanner.publish import (
    _discord_embed,
    _extract_slug,
    _find_preview,
    _layout_from_verdict,
    _uploader_alias,
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


def test_find_preview_single_image_any_name(tmp_path):
    """A lone image (any name, anywhere) is taken as the preview."""
    zp = _build(tmp_path / "p.zip", {
        "Mi-24P/Skin/description.lua": b"livery={}\n",
        "Mi-24P/Skin/tex.dds": b"DDS\0",
        "Mi-24P/Skin/my-screenshot.png": b"PNG",
    })
    assert _find_preview(zp) == "Mi-24P/Skin/my-screenshot.png"


def test_find_preview_dds_does_not_count(tmp_path):
    zp = _build(tmp_path / "p.zip", {
        "Mi-24P/Skin/description.lua": b"livery={}\n",
        "Mi-24P/Skin/tex.dds": b"DDS\0",
    })
    assert _find_preview(zp) is None


def test_find_preview_multiple_prefers_preview_name(tmp_path):
    zp = _build(tmp_path / "p.zip", {
        "Skin/preview.jpg": b"JPG",
        "Skin/extra-shot.jpg": b"JPG",
        "Skin/another.png": b"PNG",
    })
    assert _find_preview(zp) == "Skin/preview.jpg"


def test_find_preview_multiple_ambiguous_returns_none(tmp_path):
    zp = _build(tmp_path / "p.zip", {
        "Skin/shot1.jpg": b"JPG",
        "Skin/shot2.png": b"PNG",
    })
    assert _find_preview(zp) is None


# ----- uploader anonymization ----------------------------------------


def test_alias_stable_and_case_insensitive(monkeypatch):
    monkeypatch.setenv("UPLOADER_EMAIL", "Ryot@example.com")
    monkeypatch.delenv("UPLOADER_ID", raising=False)
    a = _uploader_alias()
    monkeypatch.setenv("UPLOADER_EMAIL", "ryot@example.com")  # different case
    assert _uploader_alias() == a          # same submitter -> same alias
    assert "ryot" not in a.lower()         # alias must not leak the email
    # "<Callsign> N-M", e.g. "Maverick 1-1"
    assert re.match(r"^[A-Za-z]+ [1-9]-[1-4]$", a), a


def test_alias_differs_per_submitter(monkeypatch):
    aliases = set()
    for n in range(6):
        monkeypatch.setenv("UPLOADER_EMAIL", f"submitter{n}@example.com")
        aliases.add(_uploader_alias())
    # deterministic per submitter, and distinct enough across a handful
    assert len(aliases) >= 5


def test_embed_does_not_leak_email(monkeypatch):
    monkeypatch.setenv("UPLOADER_EMAIL", "secret@example.com")
    monkeypatch.setenv("UPLOADER_ID", "7")
    verdict = {"sample": {"sha256": "a" * 64, "bytes": 123}}
    payload = _discord_embed(["UH-1H"], [("UH-1H", "Skin", "UH-1H/Skin/")],
                             verdict, published=True)
    blob = _json.dumps(payload)
    assert "secret@example.com" not in blob
    assert _uploader_alias() in blob
