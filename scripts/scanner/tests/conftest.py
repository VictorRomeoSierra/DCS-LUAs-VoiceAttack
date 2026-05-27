"""Test fixtures for the scanner.

Each fixture builds a small zip on the fly into a session-scoped
temp dir. The fixtures cover the attack patterns we want to catch
plus a happy-path baseline. PLAN.md's fixture list is the
reference -- add new ones here whenever we encounter a new bypass.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

import pytest


# A minimal valid DCS description.lua. Used as the baseline body
# for all clean-ish fixtures; attack variants edit specific bits.
CLEAN_DESCRIPTION_LUA = """\
livery = {
    {"texture_main", 0, "main_diffuse", false},
    {"texture_main", ROUGHNESS_METALLIC, "main_rm", false},
}
name = "VRS Test Livery"
countries = {"USA"}
"""


def _build_dds_header(width: int = 1024, height: int = 1024) -> bytes:
    """Construct a valid 128-byte DDS header for testing. We don't
    need the data section -- the scanner only reads the first 128
    bytes."""
    # Magic + 124-byte header. struct fields: size, flags, height,
    # width, pitch, depth, mipmaps, reserved1[11], pixelformat (32),
    # caps (16), reserved2 (4).
    header = bytearray(128)
    header[0:4] = b"DDS "
    struct.pack_into("<IIII", header, 4,
                     124,        # dwSize
                     0x000A1007, # dwFlags (CAPS|HEIGHT|WIDTH|PIXELFORMAT|MIPMAPCOUNT|LINEARSIZE)
                     height,
                     width)
    return bytes(header)


def _make_zip(out_path: Path, entries: dict[str, bytes | str]) -> Path:
    """Write a zip with the given {arcname: content} mapping."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as zf:
        for arcname, content in entries.items():
            if isinstance(content, str):
                content = content.encode("utf-8")
            zf.writestr(arcname, content)
    return out_path


@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("scanner-fixtures")


@pytest.fixture(scope="session")
def clean_livery(fixtures_dir: Path) -> Path:
    """Happy path: well-formed livery zip the scanner should pass."""
    return _make_zip(fixtures_dir / "clean-livery.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-001/description.lua":
            CLEAN_DESCRIPTION_LUA,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-001/main_diffuse.dds":
            _build_dds_header(2048, 2048) + b"\x00" * 1024,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-001/main_rm.dds":
            _build_dds_header(2048, 2048) + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def lua_os_execute(fixtures_dir: Path) -> Path:
    """Direct RCE attempt: `os.execute('calc.exe')` in description.lua."""
    bad = CLEAN_DESCRIPTION_LUA + "\nos.execute('calc.exe')\n"
    return _make_zip(fixtures_dir / "lua-os-execute.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-002/description.lua": bad,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-002/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def lua_io_open(fixtures_dir: Path) -> Path:
    """File-IO attempt: `io.open(...)` in description.lua."""
    bad = CLEAN_DESCRIPTION_LUA + "\nlocal f = io.open('C:/Windows/secret.txt', 'r')\n"
    return _make_zip(fixtures_dir / "lua-io-open.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-003/description.lua": bad,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-003/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def lua_loadstring(fixtures_dir: Path) -> Path:
    """Indirection via loadstring -- payload is a string at runtime."""
    bad = CLEAN_DESCRIPTION_LUA + "\nloadstring('os.execute(\"calc\")')()\n"
    return _make_zip(fixtures_dir / "lua-loadstring.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-004/description.lua": bad,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-004/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def lua_shadow_os(fixtures_dir: Path) -> Path:
    """Scanner evasion: `local os = require('os')` then use it."""
    bad = CLEAN_DESCRIPTION_LUA + "\nlocal os = {}\nos.execute('calc')\n"
    return _make_zip(fixtures_dir / "lua-shadow-os.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-005/description.lua": bad,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-005/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def lua_method_call(fixtures_dir: Path) -> Path:
    """Method-call form: `io:open(...)` -- different AST node than
    `io.open(...)`. Scanner must still flag the `io` reference."""
    bad = CLEAN_DESCRIPTION_LUA + "\nlocal handle = io:open('x', 'w')\n"
    return _make_zip(fixtures_dir / "lua-method-call.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-006/description.lua": bad,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-006/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })


@pytest.fixture(scope="session")
def zip_path_traversal(fixtures_dir: Path) -> Path:
    """Entry name contains `..` -- attempt to escape the destination."""
    return _make_zip(fixtures_dir / "zip-path-traversal.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-007/description.lua":
            CLEAN_DESCRIPTION_LUA,
        "../../Windows/System32/evil.dll": b"\x00" * 256,
    })


@pytest.fixture(scope="session")
def exe_payload(fixtures_dir: Path) -> Path:
    """An .exe extension in the zip -- not in the allowlist."""
    return _make_zip(fixtures_dir / "exe-payload.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-008/description.lua":
            CLEAN_DESCRIPTION_LUA,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-008/payload.exe":
            b"MZ" + b"\x00" * 254,
    })


@pytest.fixture(scope="session")
def dds_bomb(fixtures_dir: Path) -> Path:
    """DDS header claiming 100k x 100k texture -- absurd dimension."""
    huge = _build_dds_header(width=100_000, height=100_000) + b"\x00" * 1024
    return _make_zip(fixtures_dir / "dds-bomb.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-009/description.lua":
            CLEAN_DESCRIPTION_LUA,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-009/main.dds": huge,
    })


@pytest.fixture(scope="session")
def encrypted_zip(fixtures_dir: Path) -> Path:
    """A zip with the encryption bit set in the local file header
    flag_bits. Built by writing a normal zip and patching the bit
    in-place (avoids a pyzipper dependency)."""
    out = fixtures_dir / "encrypted.zip"
    _make_zip(out, {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-010/description.lua":
            CLEAN_DESCRIPTION_LUA,
    })
    # Patch the encryption bit in flag_bits for every entry, in
    # BOTH the local file header (PK\x03\x04, flag_bits at offset 6)
    # AND the central directory entry (PK\x01\x02, flag_bits at
    # offset 8). zipfile.ZipFile.infolist reads from the central
    # directory, so the CDH patch is what makes the scanner see
    # encryption -- the LFH patch is for consistency.
    data = bytearray(out.read_bytes())
    for sig, flag_field_offset in [(b"PK\x03\x04", 6), (b"PK\x01\x02", 8)]:
        pos = 0
        while True:
            idx = data.find(sig, pos)
            if idx < 0:
                break
            f = idx + flag_field_offset
            data[f] = data[f] | 0x01
            pos = idx + 4
    out.write_bytes(bytes(data))
    return out


@pytest.fixture(scope="session")
def description_in_nested_dirs(fixtures_dir: Path) -> Path:
    """An aircraft folder name containing a slash-like character --
    the F/A-18C folder is sometimes seen as `FA-18C_hornet`, but
    older liveries might have unusual nesting. This is the
    `path-with-allowed-paren.zip` case from PLAN.md: a name that's
    weird-looking but legitimate should NOT trip the scanner."""
    return _make_zip(fixtures_dir / "path-with-allowed-paren.zip", {
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-011 (variant A)/description.lua":
            CLEAN_DESCRIPTION_LUA,
        "FA-18C_hornet/Liveries/FA-18C_hornet/VRS-011 (variant A)/main.dds":
            _build_dds_header() + b"\x00" * 1024,
    })
