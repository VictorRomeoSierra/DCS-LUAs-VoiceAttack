"""Phase 2c reject: called by scan-livery.yml on a FAIL verdict.

  1. POST a Discord embed to the staff on-call channel with the
     uploader's email, the rejection reasons, and the sha256 of
     the quarantined sample on vrs.com.
  2. POST an HMAC-SHA256-signed payload to
       https://victorromeosierra.com/_internal/livery-flag.php
       { sha256, verdict, reasons, ts }
     which writes a REJECTED.json next to the raw upload in
     ~/quarantine/<sha256>/ so future tooling can list rejections.
     The endpoint itself lands in Phase 3 (it needs the ProjectSend
     cron to first quarantine samples). This script is wire-ready;
     it no-ops the POST gracefully when VRS_WEBHOOK_KEY isn't set.

The bad uploader is INTENTIONALLY not notified -- per PLAN.md
Component 5c, no feedback loop for crafting bypasses; staff
handles the human side on Discord.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

QUARANTINE_WEBHOOK_URL = (
    "https://victorromeosierra.com/_internal/livery-flag.php"
)


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


def _http_post(url: str, body: bytes, headers: dict[str, str]) -> tuple[int, str]:
    # Discord is behind Cloudflare, which 403s (error 1010) the default
    # urllib client signature -- a real User-Agent is required. Harmless
    # on our own vrs.com endpoint.
    headers = {"User-Agent": "VRS-Livery-Pipeline/1.0 (+https://victorromeosierra.com)", **headers}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def _post_discord(webhook_url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    return _http_post(
        webhook_url, body, {"Content-Type": "application/json"}
    )


def _post_quarantine_flag(verdict: dict, hmac_key: str) -> tuple[int, str]:
    """POST an HMAC-signed verdict to vrs.com livery-flag.php.

    Payload schema (also documented for the Phase 3 endpoint impl):

        { "sha256":  "<hex>",
          "verdict": "REJECT",
          "reasons": ["lua_disallowed_call:os.execute", ...],
          "ts":      <unix-seconds, integer> }

    Signature: hex(HMAC-SHA256(key, body)) in X-VRS-Signature header.
    Endpoint MUST reject if |now - ts| > 300s to bound replay window.
    """
    payload = {
        "sha256": verdict["sample"]["sha256"],
        "verdict": "REJECT",
        "reasons": [f["reason"] for f in verdict["findings"]],
        "ts": int(time.time()),
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(
        hmac_key.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return _http_post(
        QUARANTINE_WEBHOOK_URL,
        body,
        {
            "Content-Type": "application/json",
            "X-VRS-Signature": sig,
        },
    )


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
        if body and code not in (200, 204):
            lines.append(f"- body: `{body[:300]}`")
    else:
        lines.append("")
        lines.append("### Discord POST: **skipped** (DISCORD_STAFF_WEBHOOK not set)")

    hmac_key = os.environ.get("VRS_WEBHOOK_KEY", "").strip()
    if hmac_key:
        code, body = _post_quarantine_flag(verdict, hmac_key)
        lines.append("")
        lines.append("### vrs.com quarantine flag POST")
        lines.append(f"- url: `{QUARANTINE_WEBHOOK_URL}`")
        lines.append(f"- status: `{code}`")
        if body and code not in (200, 204):
            lines.append(f"- body: `{body[:300]}`")
    else:
        lines.append("")
        lines.append(
            "### vrs.com quarantine flag POST: **skipped** "
            "(VRS_WEBHOOK_KEY not set -- endpoint also doesn't exist "
            "yet; lands in Phase 3)"
        )

    summary = "\n".join(lines) + "\n"
    print(summary)
    _github_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
