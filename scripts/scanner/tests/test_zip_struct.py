"""tier-3 size/count + zip-bomb guard tests.

Real livery packs are large but only ~2:1 compressible; a zip bomb is
small-compressed and huge-uncompressed. The absolute cap bounds disk;
the ratio guard catches bombs regardless of absolute size. Constants are
monkeypatched small so the fixtures stay tiny.
"""

from __future__ import annotations

import zipfile

from scripts.scanner.checks import zip_struct


def _zip(tmp_path, name, members):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as zf:
        for n, data in members.items():
            zf.writestr(n, data)
    return zipfile.ZipFile(p, "r")


def test_normal_pack_passes(tmp_path):
    # ~2:1 incompressible-ish content, modest size -> no findings.
    import os
    zf = _zip(tmp_path, "ok.zip", {
        "FA-18C_hornet/Skin/tex.dds": os.urandom(200_000),
        "FA-18C_hornet/Skin/description.lua": b"livery={}\n",
    })
    assert zip_struct.tier3_size_count(zf) == []


def test_size_bomb_absolute(tmp_path, monkeypatch):
    monkeypatch.setattr(zip_struct, "MAX_TOTAL_SIZE", 1000)
    import os
    zf = _zip(tmp_path, "big.zip", {"a/tex.dds": os.urandom(4000)})
    reasons = [f.reason for f in zip_struct.tier3_size_count(zf)]
    assert "size_bomb" in reasons


def test_size_bomb_ratio(tmp_path, monkeypatch):
    # Highly compressible payload above the (lowered) ratio floor.
    monkeypatch.setattr(zip_struct, "RATIO_CHECK_FLOOR", 1000)
    monkeypatch.setattr(zip_struct, "MAX_COMPRESSION_RATIO", 10)
    zf = _zip(tmp_path, "bomb.zip", {"a/z.dds": b"\0" * 5_000_000})
    reasons = [f.reason for f in zip_struct.tier3_size_count(zf)]
    assert "size_bomb_ratio" in reasons


def test_count_bomb(tmp_path, monkeypatch):
    monkeypatch.setattr(zip_struct, "MAX_FILE_COUNT", 3)
    zf = _zip(tmp_path, "many.zip", {f"a/{i}.dds": b"x" for i in range(5)})
    reasons = [f.reason for f in zip_struct.tier3_size_count(zf)]
    assert "count_bomb" in reasons
