"""Scanner CLI orchestrator.

Runs the tiered checks against a candidate livery zip and emits a
Verdict (JSON or human-readable). Used by the Phase 2 GHA workflow
to gate liveries uploaded via ProjectSend before publishing them to
the per-aircraft sub-packs.

Tier order (PLAN.md):
  1. Zip integrity         (zip_struct.tier1_integrity)
  2. File-type allowlist   (zip_struct.tier2_extensions)
  3. Size/count heuristics (zip_struct.tier3_size_count)
  4. Lua AST scan          (lua_ast.scan_zip_descriptions)
  5. DDS header validation (dds_header.scan_zip)
  6. ClamAV scan           (av.scan_zip)

Tier 1 is a gate: if integrity fails, we cannot trust the entry
list, so tiers 2-6 are skipped. Tiers 2-6 all run and collect
findings -- a single sample can be rejected for multiple reasons
at once.

Exit codes:
  0  -- passed
  64 -- invalid input (file not found, not a zip, etc.)
  65 -- scanner rejected the sample (verdict.passed is False)
  66 -- scanner internal error
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

from .checks import av, dds_header, lua_ast, zip_struct
from .verdict import Finding, Verdict


def _sample_meta(zip_path: Path) -> dict:
    sha = hashlib.sha256()
    size = 0
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha.update(chunk)
            size += len(chunk)
    return {
        "path": str(zip_path),
        "bytes": size,
        "sha256": sha.hexdigest(),
    }


def scan(zip_path: Path, *, skip_av: bool = False) -> Verdict:
    """Run all tiers against `zip_path` and return a Verdict."""
    sample = _sample_meta(zip_path)

    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile as e:
        return Verdict(
            passed=False,
            findings=[Finding(tier=1, reason="zip_malformed", detail=str(e))],
            sample=sample,
        )

    findings: list[Finding] = []
    with zf:
        sample["entry_count"] = len(zf.infolist())

        # Tier 1 first -- it gates everything else.
        tier1 = zip_struct.tier1_integrity(zf)
        findings.extend(tier1)
        if tier1:
            # If integrity is broken, the entry list is unreliable;
            # don't run downstream tiers.
            return Verdict(passed=False, findings=findings, sample=sample)

        findings.extend(zip_struct.tier2_extensions(zf))
        findings.extend(zip_struct.tier3_size_count(zf))
        findings.extend(lua_ast.scan_zip_descriptions(zf))
        findings.extend(dds_header.scan_zip(zf))
        if not skip_av:
            findings.extend(av.scan_zip(zf))

    return Verdict(passed=not findings, findings=findings, sample=sample)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="livery zip to scan")
    parser.add_argument("--json", action="store_true",
                        help="emit verdict as JSON on stdout (default: human-readable)")
    parser.add_argument("--skip-av", action="store_true",
                        help="skip ClamAV tier (useful for fast local dev)")
    args = parser.parse_args(argv)

    if not args.zip.is_file():
        print(f"error: not a file: {args.zip}", file=sys.stderr)
        return 64

    try:
        verdict = scan(args.zip, skip_av=args.skip_av)
    except Exception as e:
        print(f"scanner error: {type(e).__name__}: {e}", file=sys.stderr)
        return 66

    if args.json:
        print(verdict.to_json())
    else:
        status = "PASS" if verdict.passed else "REJECT"
        print(f"[{status}] {args.zip}")
        print(f"  sha256: {verdict.sample['sha256']}")
        print(f"  bytes:  {verdict.sample['bytes']:,}")
        print(f"  entries: {verdict.sample.get('entry_count', '?')}")
        if verdict.findings:
            print(f"  findings ({len(verdict.findings)}):")
            for f in verdict.findings:
                print(f"    tier {f.tier}: {f.reason}")
                if f.detail:
                    print(f"        {f.detail}")
        else:
            print("  no findings")

    return 0 if verdict.passed else 65


if __name__ == "__main__":
    sys.exit(main())
