#!/usr/bin/env python3
"""Phase 3 ingest cron: ProjectSend upload -> scan-livery dispatch.

Runs on vrs.com every ~2 minutes. Detects new ProjectSend uploads
past a watermark, quarantines each raw blob outside the web root,
mints a short-lived signed URL, and fires the scan-livery workflow
with the inputs it already expects. The workflow scans + publishes
(pass) or alerts staff (fail); this cron is purely the front half.

Deploy to: ~/bin/livery-pipeline-cron.py on vrs.com (python3.12).
Cron entry:
    */2 * * * * /usr/bin/python3.12 /home/customdc/bin/livery-pipeline-cron.py \
        >> /home/customdc/cron-state/livery-pipeline.log 2>&1

Serialization (three independent layers, so we never publish two at
once -- concurrent publishes would race on manifest.json + the main
push):
  1. flock on ~/cron-state/.lock -- one tick at a time.
  2. GitHub API check: defer if any scan-livery run is queued OR
     in_progress.
  3. At most ONE dispatch per tick, even when the API shows zero
     active (covers the queued-creation window).

Watermark (~/cron-state/livery-pipeline.json = {"ts","id"}):
  - Missing file -> seed to the current DB max and exit WITHOUT
    dispatching. Backfilling history is an explicit action: write the
    watermark to an earlier {ts,id} by hand, then let the cron run.
  - Advanced only after a successful dispatch (or when skipping a
    superseded/missing row), so a failed dispatch retries next tick.

Secrets (files, never argv/env-echoed):
  - ~/.vrs-pipeline-secrets/gh-token  -- fine-grained PAT, actions:write
  DB creds stay inside livery-db-query.php (ProjectSend's config).
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
REPO = "VictorRomeoSierra/VRSMods"
WORKFLOW = "scan-livery.yml"
REF = "main"

DB_HELPER = HOME / "bin" / "livery-db-query.php"
STORE_BASE = HOME / "public_html" / "upload" / "upload" / "files"
QUARANTINE = HOME / "quarantine"
SIGNED_URLS = QUARANTINE / "_signed-urls"
CRON_STATE = HOME / "cron-state"
WATERMARK = CRON_STATE / "livery-pipeline.json"
LOCKFILE = CRON_STATE / ".lock"
PAT_FILE = HOME / ".vrs-pipeline-secrets" / "gh-token"

BLOB_URL_BASE = "https://victorromeosierra.com/_internal/livery-blob.php"
TOKEN_TTL = 900  # 15 minutes

API = "https://api.github.com"

# Contributor naming convention for superseded uploads: they rename the
# display filename to flag it (e.g. id 18 -> "Old - Do Not Use -.zip").
DO_NOT_USE = re.compile(r"old\s*-?\s*do\s*not\s*use", re.IGNORECASE)


def log(msg: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{stamp}] {msg}", flush=True)


# ----- GitHub API ----------------------------------------------------


def _headers(pat: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "vrs-livery-cron",
    }


def _api_get(pat: str, path: str) -> tuple[int, dict]:
    req = urllib.request.Request(API + path, headers=_headers(pat))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:  # noqa: BLE001
        log(f"api GET {path} error: {type(e).__name__}: {e}")
        return -1, {}


def active_runs(pat: str) -> int:
    """Count scan-livery runs that are queued or in_progress.

    Raises on API error -- caller treats that as 'defer this tick'
    rather than risk dispatching into a race.
    """
    total = 0
    for status in ("queued", "in_progress"):
        st, data = _api_get(
            pat,
            f"/repos/{REPO}/actions/workflows/{WORKFLOW}/runs"
            f"?status={status}&per_page=1",
        )
        if st != 200:
            raise SystemExit(f"runs query failed (HTTP {st}); deferring tick")
        total += int(data.get("total_count", 0))
    return total


def dispatch(pat: str, inputs: dict[str, str]) -> bool:
    body = json.dumps({"ref": REF, "inputs": inputs}).encode("utf-8")
    req = urllib.request.Request(
        API + f"/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
        data=body,
        method="POST",
        headers={**_headers(pat), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status in (201, 204)
    except urllib.error.HTTPError as e:
        log(f"dispatch HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        return False
    except Exception as e:  # noqa: BLE001
        log(f"dispatch error: {type(e).__name__}: {e}")
        return False


# ----- DB helper -----------------------------------------------------


def php_helper(mode: str, *args: str):
    proc = subprocess.run(
        ["php", str(DB_HELPER), mode, *args],
        capture_output=True, text=True, timeout=60,
    )
    out = proc.stdout.strip()
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit(
            f"db helper non-JSON (rc={proc.returncode}): "
            f"{out[:300]} | stderr={proc.stderr[:300]}"
        )
    if isinstance(data, dict) and "error" in data:
        raise SystemExit(f"db helper error: {data['error']}")
    return data


# ----- file / quarantine / token ------------------------------------


def resolve_file(row: dict) -> Path | None:
    url = row["url"]
    y, m = row.get("disk_folder_year"), row.get("disk_folder_month")
    candidates: list[Path] = []
    if y and m:
        candidates.append(STORE_BASE / f"{y:04d}" / f"{int(m):02d}" / url)
        candidates.append(STORE_BASE / str(y) / str(m) / url)
    candidates.append(STORE_BASE / url)
    for c in candidates:
        if c.is_file():
            return c
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def quarantine_file(src: Path, sha: str, row: dict) -> None:
    qdir = QUARANTINE / sha
    qdir.mkdir(parents=True, exist_ok=True)
    dest = qdir / "original.zip"
    if not dest.exists():
        shutil.copyfile(src, dest)
    meta = {
        "upload_id": row["id"],
        "user_id": row["user_id"],
        "uploader_email": row.get("uploader_email"),
        "uploader_user": row.get("uploader_user"),
        "original_filename": row.get("original_url"),
        "stored_url": row["url"],
        "sha256": sha,
        "size": row.get("size"),
        "ts": row["ts"],
        "quarantined_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (qdir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def mint_token(sha: str) -> str:
    token = secrets.token_hex(32)
    payload = {"sha256": sha, "expires": int(time.time()) + TOKEN_TTL}
    (SIGNED_URLS / f"{token}.json").write_text(
        json.dumps(payload) + "\n", encoding="utf-8"
    )
    return token


def clean_expired_tokens() -> None:
    if not SIGNED_URLS.is_dir():
        return
    now = int(time.time())
    for f in SIGNED_URLS.glob("*.json"):
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("expires", 0) < now:
                f.unlink()
        except Exception:  # noqa: BLE001
            f.unlink()  # malformed -> drop


# ----- watermark -----------------------------------------------------


def load_watermark() -> dict | None:
    if not WATERMARK.is_file():
        return None
    return json.loads(WATERMARK.read_text(encoding="utf-8"))


def save_watermark(ts: str, file_id: int) -> None:
    WATERMARK.write_text(
        json.dumps({"ts": ts, "id": file_id}, indent=2) + "\n", encoding="utf-8"
    )


# ----- main ----------------------------------------------------------


def main() -> int:
    for d in (CRON_STATE, QUARANTINE, SIGNED_URLS):
        d.mkdir(parents=True, exist_ok=True)

    # Layer 1: only one tick at a time.
    lock_fd = open(LOCKFILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("another tick holds the lock; exiting")
        return 0

    clean_expired_tokens()

    if not PAT_FILE.is_file():
        raise SystemExit(f"missing PAT: {PAT_FILE}")
    pat = PAT_FILE.read_text(encoding="utf-8").strip()

    # Layer 2: defer if any scan is queued/in_progress.
    n_active = active_runs(pat)
    if n_active:
        log(f"{n_active} scan-livery run(s) active; deferring")
        return 0

    wm = load_watermark()
    if wm is None:
        seed = php_helper("seed")
        save_watermark(seed["ts"], int(seed["id"]))
        log(f"seeded watermark -> {seed['ts']}/{seed['id']} (no dispatch on first run)")
        return 0

    rows = php_helper("query", wm["ts"], str(wm["id"]))
    if not rows:
        log("no new uploads")
        return 0

    for row in rows:
        name = row.get("filename") or row.get("original_url") or ""

        if DO_NOT_USE.search(name):
            log(f"skip id {row['id']} (superseded: {name!r}); advancing")
            save_watermark(row["ts"], row["id"])
            continue

        path = resolve_file(row)
        if path is None:
            log(f"WARN id {row['id']}: file not found (url={row['url']!r}); advancing past")
            save_watermark(row["ts"], row["id"])
            continue

        sha = sha256_file(path)
        quarantine_file(path, sha, row)
        token = mint_token(sha)
        inputs = {
            "sha256": sha,
            "signed_url": f"{BLOB_URL_BASE}?token={token}",
            "uploader_email": row.get("uploader_email") or "unknown@victorromeosierra.com",
            "uploader_id": str(row["user_id"]),
            "original_filename": row.get("original_url") or name or "upload.zip",
            "upload_id": str(row["id"]),
        }
        if not dispatch(pat, inputs):
            log(f"dispatch FAILED id {row['id']}; NOT advancing (retry next tick)")
            return 1
        save_watermark(row["ts"], row["id"])
        log(f"dispatched id {row['id']} ({name}) sha={sha[:12]} -> watermark {row['ts']}/{row['id']}")
        # Layer 3: one dispatch per tick.
        break

    return 0


if __name__ == "__main__":
    sys.exit(main())
