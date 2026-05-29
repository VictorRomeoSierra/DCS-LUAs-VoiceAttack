"""description.lua static-scan tests (tier 4).

Guards the allowlist against two failure modes: rejecting legitimate
livery data (false positive -> a real livery can't publish) and
accepting code execution (false negative -> malware ships).
"""

from __future__ import annotations

from scripts.scanner.checks.lua_ast import scan_source

_REAL_LIVERY = """
livery = {
  {"F18C_1", 0, "F18C_1_DIFF", true},
}
name = "VFA-103 Jolly Rogers"
countries = {"USA"}
custom_args = { [38] = 0.0, [400] = 1.0 }
"""


def test_custom_args_is_allowed():
    # custom_args is standard DCS livery data -- must not be rejected.
    findings = scan_source(_REAL_LIVERY)
    assert findings == [], [f.reason for f in findings]


def test_unknown_property_still_rejected():
    findings = scan_source("evil_payload = 1\n")
    assert any(f.reason == "lua_unknown_property:evil_payload" for f in findings)


def test_os_execute_still_rejected():
    findings = scan_source('name = "x"\nos.execute("rm -rf /")\n')
    assert any(f.reason.startswith("lua_disallowed") for f in findings)
