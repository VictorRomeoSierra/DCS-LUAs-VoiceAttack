"""Phase 2 publish stub: called by scan-livery.yml on PASS verdict.

Real responsibilities (Phase 2c):

  1. Read the verdict.json + the candidate livery zip.
  2. Identify the target aircraft from the zip's top-level folder.
  3. SSH push the livery content into
     vrs.com:~/livery-source/<Aircraft>/<slug>/
  4. Rebuild ONLY the affected <Aircraft>.zip
     (`~/bin/build-aircraft-packs.py --only <Aircraft>`).
  5. Compute the new bytes + xxhsum (returned by the rebuild script).
  6. Update liveries-index/<Aircraft>/pack.json; commit + push.
  7. Regenerate the three repo manifests
     (`python scripts/build-repo.py`) and scp them to vrs.com.
  8. POST a Discord embed to the #liveries webhook -- the published
     livery + uploader handle + preview thumbnail (if `preview.jpg`
     was supplied in the upload).

For Phase 2b this script is a STUB. It reads the verdict + does
basic inspection and emits a structured summary to
$GITHUB_STEP_SUMMARY so the workflow run page is useful. The real
SSH + git + Discord work is deferred until:

  - The dedicated ed25519 SSH key is minted and added as
    secrets.VRS_SSH_KEY with `command=` restriction on vrs.com.
  - The Discord webhook URL is added as
    secrets.DISCORD_LIVERIES_WEBHOOK.
  - A fine-grained GitHub PAT is configured for the actions
    runner to commit pack.json updates back to main.

When any of those is missing, the stub logs that it would have
done X and exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path


def _github_summary(text: str) -> None:
    """Append to the GHA run-page summary if running in Actions."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _identify_aircraft(zip_path: Path) -> str | None:
    """Find the aircraft name from the zip's top-level folder.

    Per the Phase 1 OvGME convention, livery zips have outer
    structure `<Aircraft>/Liveries/<Aircraft>/<livery>/...`. The
    outer folder is the aircraft. For uploaded liveries that
    haven't been wrapped yet, the structure may be just
    `<Aircraft>/<livery>/...` -- same answer.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        roots = set()
        for info in zf.infolist():
            parts = info.filename.replace("\\", "/").split("/", 1)
            if parts and parts[0]:
                roots.add(parts[0])
    if len(roots) == 1:
        return roots.pop()
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="candidate livery zip")
    parser.add_argument("verdict", type=Path, help="verdict.json from scan.py")
    args = parser.parse_args(argv)

    verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    aircraft = _identify_aircraft(args.zip)

    have_ssh = bool(os.environ.get("VRS_SSH_KEY"))
    have_webhook = bool(os.environ.get("DISCORD_LIVERIES_WEBHOOK"))

    lines = [
        "## Publish (stub)",
        "",
        f"- **Verdict:** PASS",
        f"- **Aircraft:** `{aircraft or 'unknown'}`",
        f"- **Sample sha256:** `{verdict['sample']['sha256']}`",
        f"- **Sample bytes:** {verdict['sample']['bytes']:,}",
        f"- **Uploader:** {os.environ.get('UPLOADER_EMAIL', 'unknown')} "
        f"(id {os.environ.get('UPLOADER_ID', '?')})",
        f"- **Original filename:** `{os.environ.get('ORIGINAL_FILENAME', '?')}`",
        "",
        "### What this stub would do (Phase 2c):",
        "",
        "1. SSH push to `vrs.com:~/livery-source/" + (aircraft or "<Aircraft>") + "/<slug>/`",
        "2. Rebuild `" + (aircraft or "<Aircraft>") + ".zip` on vrs.com",
        "3. Update `liveries-index/" + (aircraft or "<Aircraft>") + "/pack.json` + git push",
        "4. Regenerate + scp the three repo manifests",
        "5. POST Discord embed to `#liveries`",
        "",
        "### Secrets available in this run:",
        "",
        f"- VRS_SSH_KEY: {'set' if have_ssh else '**NOT SET**'}",
        f"- DISCORD_LIVERIES_WEBHOOK: {'set' if have_webhook else '**NOT SET**'}",
    ]
    summary = "\n".join(lines) + "\n"

    print(summary)
    _github_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
