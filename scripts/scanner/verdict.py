"""Data classes for scanner verdicts.

A `Verdict` is the scanner's full output: whether the sample passed,
and the list of `Finding`s recorded. Each `Finding` is a single
reason a sample was rejected (or a soft warning). The scanner runs
checks in tiers and short-circuits to the next sample once any tier
produces findings -- but within a tier, all findings are collected
(so a single sample can be rejected for multiple reasons in one go).

Serialised as JSON for the GHA workflow to consume.
"""

from __future__ import annotations

import dataclasses
import json


@dataclasses.dataclass
class Finding:
    """A single rejection reason.

    `tier` identifies which scanner tier (1-6 per PLAN.md) produced
    the finding. `reason` is a short stable identifier like
    `zip_path_traversal` or `lua_disallowed_call:os.execute` -- meant
    for programmatic consumption. `detail` is human-readable extra
    info shown in Discord alerts.
    """
    tier: int
    reason: str
    detail: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Verdict:
    passed: bool
    findings: list[Finding]
    sample: dict  # bytes, sha256, entry_count, etc.
    layout: dict | None = None  # resolved {liveries, aircraft}; set only on a clean layout

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "findings": [f.to_dict() for f in self.findings],
            "sample": self.sample,
            "layout": self.layout,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
