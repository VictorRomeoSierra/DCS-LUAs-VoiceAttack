"""End-to-end tests for the scanner.

Each test takes a fixture-built zip and asserts the scanner's
verdict matches expectations. Reject tests pin down which reason
code the scanner should produce -- changing a reason code without
updating the test is a breaking API change for downstream
(Discord embeds, on-call summaries).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# scan() is the in-process entrypoint -- tests use it directly so
# we don't fork a subprocess for every fixture.
from scripts.scanner.scan import scan


def _reasons(verdict) -> set[str]:
    return {f.reason for f in verdict.findings}


# ----- Happy path -----

def test_clean_livery_passes(clean_livery: Path):
    v = scan(clean_livery, skip_av=True)
    assert v.passed, f"unexpected findings: {[f.reason for f in v.findings]}"
    assert not v.findings


def test_description_in_nested_dirs_passes(description_in_nested_dirs: Path):
    """Weird-looking but legitimate folder names shouldn't trip tier 1."""
    v = scan(description_in_nested_dirs, skip_av=True)
    assert v.passed, f"unexpected findings: {[f.reason for f in v.findings]}"


# ----- Tier 1: zip integrity -----

def test_zip_path_traversal_rejected(zip_path_traversal: Path):
    v = scan(zip_path_traversal, skip_av=True)
    assert not v.passed
    assert "zip_path_traversal" in _reasons(v)


def test_encrypted_zip_rejected(encrypted_zip: Path):
    v = scan(encrypted_zip, skip_av=True)
    assert not v.passed
    assert "zip_encrypted" in _reasons(v)


# ----- Tier 2: file-type allowlist -----

def test_exe_payload_rejected(exe_payload: Path):
    v = scan(exe_payload, skip_av=True)
    assert not v.passed
    assert "disallowed_extension:.exe" in _reasons(v)


# ----- Tier 4: Lua AST -----

def test_lua_os_execute_rejected(lua_os_execute: Path):
    v = scan(lua_os_execute, skip_av=True)
    assert not v.passed
    # The `os` reference fires lua_disallowed_name:os; the
    # os.execute index expression fires lua_disallowed_call:os.execute.
    # Either is sufficient; in practice we get both.
    reasons = _reasons(v)
    assert any(r.startswith("lua_disallowed_") and "os" in r for r in reasons), reasons


def test_lua_io_open_rejected(lua_io_open: Path):
    v = scan(lua_io_open, skip_av=True)
    assert not v.passed
    reasons = _reasons(v)
    assert any("io" in r for r in reasons), reasons


def test_lua_loadstring_rejected(lua_loadstring: Path):
    v = scan(lua_loadstring, skip_av=True)
    assert not v.passed
    reasons = _reasons(v)
    assert "lua_disallowed_name:loadstring" in reasons, reasons


def test_lua_shadow_os_rejected(lua_shadow_os: Path):
    v = scan(lua_shadow_os, skip_av=True)
    assert not v.passed
    reasons = _reasons(v)
    assert "lua_shadow:os" in reasons, reasons


def test_lua_method_call_rejected(lua_method_call: Path):
    v = scan(lua_method_call, skip_av=True)
    assert not v.passed
    reasons = _reasons(v)
    assert any("io" in r for r in reasons), reasons


# ----- Tier 5: DDS header -----

def test_dds_bomb_rejected(dds_bomb: Path):
    v = scan(dds_bomb, skip_av=True)
    assert not v.passed
    assert "dds_invalid" in _reasons(v)
