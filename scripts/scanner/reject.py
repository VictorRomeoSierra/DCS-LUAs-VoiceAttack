"""Phase 2 reject stub: called by scan-livery.yml on FAIL verdict.

Real responsibilities (Phase 2c):

  1. POST a Discord embed to the staff on-call channel:
       <@&ONCALL_ROLE_ID> Upload from <uploader> rejected
       Reason codes: lua_disallowed_call:os.execute, ...
       SHA256: <hex>
       Quarantined at vrs.com:~/quarantine/<sha256>/
  2. POST an HMAC-signed payload to vrs.com:
       /_internal/livery-flag.php  { sha256, reasons, verdict }
     which writes a REJECTED.json next to the raw upload in
     ~/quarantine/<sha256>/ so future tooling can list rejections.

The bad uploader is INTENTIONALLY not notified -- per PLAN.md
Component 5c, no feedback loop for crafting bypasses; staff
handles the human side on Discord.

For Phase 2b this is a STUB. It assembles the would-be Discord
embed payload, logs it to the GHA step summary, and POSTs to
DISCORD_STAFF_WEBHOOK if that secret is set. The vrs.com
quarantine webhook is deferred until Phase 3 (it needs the
ProjectSend cron to first land samples in ~/quarantine/).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path


def _github_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _build_discord_embed(verdict: dict) -> dict:
    reasons = "\n".join(f"- `{f['reason']}`" for f in verdict["findings"][:25])
    if len(verdict["findings"]) > 25:
        reasons += f"\n- _... and {len(verdict['findings']) - 25} more_"

    role_id = os.environ.get("DISCORD_ONCALL_ROLE_ID", "").strip()
    content = f"<@&{role_id}>" if role_id else ""

    return {
        "content": content or None,
        "embeds": [{
            "title": "Livery upload REJECTED",
            "description": (
                f"Static scan flagged a livery from "
                f"**{os.environ.get('UPLOADER_EMAIL', 'unknown')}**."
            ),
            "color": 15158332,  # red
            "fields": [
                {
                    "name": "ProjectSend upload ID",
                    "value": os.environ.get("UPLOAD_ID", "?"),
                    "inline": True,
                },
                {
                    "name": "Original filename",
                    "value": f"`{os.environ.get('ORIGINAL_FILENAME', '?')}`",
                    "inline": True,
                },
                {
                    "name": "SHA256",
                    "value": f"`{verdict['sample']['sha256']}`",
                    "inline": False,
                },
                {
                    "name": f"Reasons ({len(verdict['findings'])})",
                    "value": reasons or "_(none recorded)_",
                    "inline": False,
                },
                {
                    "name": "Quarantined at",
                    "value": f"`~/quarantine/{verdict['sample']['sha256']}/` (vrs.com)",
                    "inline": False,
                },
            ],
            "footer": {
                "text": "Action: review sample, decide whether to "
                        "ban uploader and remove from ProjectSend."
            },
        }],
    }


def _post_discord(webhook_url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verdict", type=Path, help="verdict.json from scan.py")
    args = parser.parse_args(argv)

    verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    payload = _build_discord_embed(verdict)

    lines = [
        "## Reject (stub)",
        "",
        f"- **Verdict:** REJECT",
        f"- **Sample sha256:** `{verdict['sample']['sha256']}`",
        f"- **Sample bytes:** {verdict['sample']['bytes']:,}",
        f"- **Uploader:** {os.environ.get('UPLOADER_EMAIL', 'unknown')} "
        f"(id {os.environ.get('UPLOADER_ID', '?')})",
        f"- **Original filename:** `{os.environ.get('ORIGINAL_FILENAME', '?')}`",
        "",
        f"### Findings ({len(verdict['findings'])})",
        "",
    ]
    for f in verdict["findings"][:20]:
        lines.append(f"- **tier {f['tier']}** `{f['reason']}` -- {f['detail']}")
    if len(verdict["findings"]) > 20:
        lines.append(f"- _... and {len(verdict['findings']) - 20} more_")

    lines.append("")
    lines.append("### Discord embed payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload, indent=2))
    lines.append("```")

    webhook = os.environ.get("DISCORD_STAFF_WEBHOOK", "").strip()
    if webhook:
        code, body = _post_discord(webhook, payload)
        lines.append("")
        lines.append("### Discord POST")
        lines.append(f"- status: `{code}`")
        if body:
            lines.append(f"- body: `{body[:300]}`")
    else:
        lines.append("")
        lines.append("### Discord POST: **skipped** (DISCORD_STAFF_WEBHOOK not set)")

    summary = "\n".join(lines) + "\n"
    print(summary)
    _github_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
