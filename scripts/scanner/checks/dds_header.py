"""DDS header validation (tier 5).

DDS files are DirectDraw Surface textures -- the format DCS uses for
livery textures. The header is well-defined (128 bytes); the
malicious pattern is a header that lies about the texture
dimensions, prompting DCS to allocate huge buffers.

We don't try to decode the pixel data -- we only check the header
is well-formed and dimensions are sane.
"""

from __future__ import annotations

import struct
import zipfile

from ..verdict import Finding

DDS_MAGIC = b"DDS "
DDS_HEADER_BYTES = 128         # magic (4) + header (124) = first 128 bytes
DDS_DECLARED_HEADER_SIZE = 124

MAX_DIMENSION = 16384          # DCS-realistic max texture edge
MAX_DECLARED_PIXELS = 16384 * 16384  # bound declared width*height


def _scan_one_dds(data: bytes, name: str) -> list[Finding]:
    findings: list[Finding] = []
    if len(data) < DDS_HEADER_BYTES:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: too short ({len(data)} bytes) to contain a DDS header",
        ))
        return findings

    magic = data[:4]
    if magic != DDS_MAGIC:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: bad magic {magic!r}, expected {DDS_MAGIC!r}",
        ))
        return findings

    # DDS_HEADER struct, after the magic:
    #   uint32 dwSize           = 124
    #   uint32 dwFlags
    #   uint32 dwHeight
    #   uint32 dwWidth
    #   uint32 dwPitchOrLinearSize
    #   uint32 dwDepth
    #   uint32 dwMipMapCount
    #   ... more fields
    try:
        size, _flags, height, width = struct.unpack_from("<IIII", data, 4)
    except struct.error as e:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: header unpack failed: {e}",
        ))
        return findings

    if size != DDS_DECLARED_HEADER_SIZE:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: declared header size {size} != 124",
        ))

    if width == 0 or height == 0:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: zero dimension ({width}x{height})",
        ))
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: dimension exceeds {MAX_DIMENSION} ({width}x{height})",
        ))
    if width * height > MAX_DECLARED_PIXELS:
        findings.append(Finding(
            tier=5, reason="dds_invalid",
            detail=f"{name}: total pixel count {width*height} is unreasonable",
        ))

    return findings


def scan_zip(zf: zipfile.ZipFile) -> list[Finding]:
    """Walk every .dds entry in the zip and run header validation.
    Reads only the first 128 bytes per entry."""
    findings: list[Finding] = []
    for info in zf.infolist():
        if info.is_dir():
            continue
        if not info.filename.lower().endswith(".dds"):
            continue
        try:
            with zf.open(info, "r") as f:
                head = f.read(DDS_HEADER_BYTES)
        except Exception as e:
            findings.append(Finding(
                tier=5, reason="dds_read_error",
                detail=f"{info.filename}: {e}"[:300],
            ))
            continue
        findings.extend(_scan_one_dds(head, info.filename))
    return findings
