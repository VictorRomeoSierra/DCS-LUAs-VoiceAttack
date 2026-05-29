"""Zip-structure checks. Tiers 1-3 per PLAN.md.

  Tier 1 -- zip integrity:
    - opens cleanly (not corrupt)
    - no encrypted entries
    - no path traversal (`..`) in entry names
    - no absolute paths (leading /, leading drive letter)

  Tier 2 -- file-type allowlist:
    - every non-directory entry's extension is in the allowed set

  Tier 3 -- size/count heuristics:
    - total uncompressed size <= 500 MB
    - <= 200 files
    - no single file > 100 MB

Each tier function takes an open ZipFile and returns a list of
Findings. Empty list = passed.
"""

from __future__ import annotations

import posixpath
import zipfile

from ..verdict import Finding

ALLOWED_EXTENSIONS = {".dds", ".lua", ".png", ".jpg", ".txt", ".json"}

# Sized for real multi-livery uploads, not single skins. DDS textures are
# large and only ~2:1 compressible, so a legit pack of a few high-res
# liveries easily clears half a GB uncompressed (e.g. the UH-60L Latvian
# pack: 3 liveries, 548 MB). The absolute cap bounds runner disk during
# extraction; the compression-ratio guard below is the actual zip-bomb
# defense (a bomb expands by thousands of x, a DDS pack by ~2x).
MAX_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB uncompressed
MAX_FILE_COUNT = 1000
MAX_SINGLE_FILE = 256 * 1024 * 1024      # 256 MB per file (8K DDS headroom)
MAX_COMPRESSION_RATIO = 100              # uncompressed/compressed; bomb guard
RATIO_CHECK_FLOOR = 50 * 1024 * 1024     # only ratio-check above 50 MB


def tier1_integrity(zf: zipfile.ZipFile) -> list[Finding]:
    """Zip-level structural sanity. Run before anything else --
    if the zip is malformed, later tiers can't trust the entry list.
    """
    findings: list[Finding] = []
    for info in zf.infolist():
        name = info.filename
        # Encryption: bit 0 of flag_bits indicates an encrypted entry.
        if info.flag_bits & 0x1:
            findings.append(Finding(
                tier=1, reason="zip_encrypted",
                detail=f"encrypted entry: {name}",
            ))
            # Don't keep walking -- the encryption flag usually means
            # we can't read the rest meaningfully.
            return findings

        # Normalise to forward slashes (some implementations write \\).
        normalised = name.replace("\\", "/")

        # Absolute paths: leading /, leading drive letter (e.g. "C:/...").
        if normalised.startswith("/"):
            findings.append(Finding(
                tier=1, reason="zip_absolute_path",
                detail=f"entry has leading slash: {name}",
            ))
        if len(normalised) >= 2 and normalised[1] == ":":
            findings.append(Finding(
                tier=1, reason="zip_absolute_path",
                detail=f"entry has drive letter: {name}",
            ))

        # Path traversal: any "../" component.
        parts = normalised.split("/")
        if ".." in parts:
            findings.append(Finding(
                tier=1, reason="zip_path_traversal",
                detail=f"entry contains '..' component: {name}",
            ))

    # testzip() returns the first bad entry name, or None if all OK.
    # Catches CRC errors etc.
    bad = zf.testzip()
    if bad is not None:
        findings.append(Finding(
            tier=1, reason="zip_malformed",
            detail=f"testzip failed on: {bad}",
        ))

    return findings


def tier2_extensions(zf: zipfile.ZipFile) -> list[Finding]:
    """Every non-directory entry must have an allowed extension."""
    findings: list[Finding] = []
    seen_bad_exts: set[str] = set()
    for info in zf.infolist():
        if info.is_dir():
            continue
        # ModPack.xml / .omp files are OMM metadata -- not part of
        # the uploaded livery payload. Allowed by convention but
        # technically reject this since liveries shouldn't be
        # carrying their own OMM definition. Keep them rejected here
        # so the scanner stays strict; the build script adds them
        # later.
        name = info.filename
        # `splitext` is dumb about names with dots in directory parts
        # ("some.dir/file"), so use posixpath which is what we want.
        _, ext = posixpath.splitext(name.lower())
        if ext == "":
            findings.append(Finding(
                tier=2, reason="disallowed_extension:none",
                detail=f"entry without extension: {name}",
            ))
            continue
        if ext not in ALLOWED_EXTENSIONS:
            if ext not in seen_bad_exts:
                findings.append(Finding(
                    tier=2, reason=f"disallowed_extension:{ext}",
                    detail=f"e.g. {name}",
                ))
                seen_bad_exts.add(ext)
    return findings


def tier3_size_count(zf: zipfile.ZipFile) -> list[Finding]:
    """Size and count limits to bound a malicious sample's blast
    radius (zip bombs, file-count DoS)."""
    findings: list[Finding] = []
    files = [i for i in zf.infolist() if not i.is_dir()]
    if len(files) > MAX_FILE_COUNT:
        findings.append(Finding(
            tier=3, reason="count_bomb",
            detail=f"{len(files)} files > limit {MAX_FILE_COUNT}",
        ))

    total = 0
    total_compressed = 0
    oversized: list[str] = []
    for info in files:
        size = info.file_size
        total += size
        total_compressed += info.compress_size
        if size > MAX_SINGLE_FILE:
            oversized.append(f"{info.filename} ({size:,} bytes)")

    if total > MAX_TOTAL_SIZE:
        findings.append(Finding(
            tier=3, reason="size_bomb",
            detail=f"total uncompressed {total:,} bytes > limit {MAX_TOTAL_SIZE:,}",
        ))
    # Zip-bomb guard: a small archive that explodes on extraction. Real
    # livery packs sit around 2x; only flag big expansions so a tiny,
    # highly-compressible-but-harmless file doesn't trip it.
    if total > RATIO_CHECK_FLOOR and total_compressed > 0:
        ratio = total / total_compressed
        if ratio > MAX_COMPRESSION_RATIO:
            findings.append(Finding(
                tier=3, reason="size_bomb_ratio",
                detail=(f"compression ratio {ratio:.0f}x "
                        f"({total:,} / {total_compressed:,} bytes) "
                        f"> limit {MAX_COMPRESSION_RATIO}x"),
            ))
    if oversized:
        findings.append(Finding(
            tier=3, reason="oversized_file",
            detail="; ".join(oversized[:5]),
        ))

    return findings
