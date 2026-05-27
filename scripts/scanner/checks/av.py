"""ClamAV scan (tier 6).

The last-line defense against known-malware payloads sneaking
through other tiers. We shell out to `clamscan` (the CLI) on the
already-extracted zip's contents. `clamscan` is the simplest
deployment -- no daemon needed (pyclamd's `clamd` is fine too but
adds a deps + service requirement).

This module is best-effort: if `clamscan` is not on PATH we return
an empty finding list rather than failing the scan. The GHA
workflow MUST ensure clamscan is installed (apt-get install clamav
+ freshclam); local dev can run without and rely on tiers 1-5
catching obvious issues.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from ..verdict import Finding


def _have_clamscan() -> bool:
    return shutil.which("clamscan") is not None


def scan_zip(zf: zipfile.ZipFile) -> list[Finding]:
    """Extract the zip contents into a temp directory and run
    `clamscan -r` over it. Parse the output for any infected files."""
    if not _have_clamscan():
        # Not a finding -- the GHA wrapper checks for clamscan
        # availability and bails before invoking this if it's
        # missing. For local dev we let it slide.
        return []

    findings: list[Finding] = []
    with tempfile.TemporaryDirectory(prefix="livery-av-") as tmp:
        tmp_path = Path(tmp)
        # Extract files only (the zip's already passed integrity
        # and path-traversal checks by this point, so extractall
        # is safe -- but use a fresh temp dir per scan).
        try:
            zf.extractall(tmp_path)
        except Exception as e:
            findings.append(Finding(
                tier=6, reason="av_extract_error",
                detail=f"could not extract for AV scan: {e}"[:300],
            ))
            return findings

        # `clamscan -r --no-summary -i` walks recursively, prints
        # only infected files (-i), and skips the trailing summary.
        try:
            proc = subprocess.run(
                ["clamscan", "-r", "--no-summary", "-i", str(tmp_path)],
                capture_output=True, text=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            findings.append(Finding(
                tier=6, reason="av_timeout",
                detail="clamscan exceeded 5-minute timeout",
            ))
            return findings
        except Exception as e:
            findings.append(Finding(
                tier=6, reason="av_error",
                detail=f"clamscan invocation failed: {e}"[:300],
            ))
            return findings

        # clamscan exit codes: 0 = clean, 1 = found virus, 2 = error.
        if proc.returncode == 0:
            return []  # clean
        if proc.returncode == 2:
            findings.append(Finding(
                tier=6, reason="av_error",
                detail=f"clamscan returned 2: {proc.stderr.strip()[:300]}",
            ))
            return findings

        # returncode == 1: virus found. Parse stdout.
        # Format per line: `<path>: <SignatureName> FOUND`
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line.endswith("FOUND"):
                continue
            try:
                path_part, signature = line.rsplit(":", 1)
                signature = signature.replace(" FOUND", "").strip()
                # Strip the tmp_path prefix for readability.
                rel = Path(path_part).relative_to(tmp_path).as_posix()
            except (ValueError, IndexError):
                rel = "?"
                signature = line
            findings.append(Finding(
                tier=6, reason=f"clamav:{signature}",
                detail=f"{rel}: {signature}",
            ))

    return findings
