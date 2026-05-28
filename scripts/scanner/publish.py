"""Phase 2c publish: push livery to vrs.com livery-source/, trigger
rebuild, update pack.json + manifests, POST Discord embed.

Called by scan-livery.yml on a PASS verdict. Each step gracefully
no-ops if its prerequisites are missing, so this script is safe to
land before the user mints the secrets.

Steps and their prereqs:

  1. Parse zip layout -> (aircraft, slugs).
     No prereqs.

  2. Stage slug content to /tmp/livery-extract/.
     No prereqs.

  3. Rsync each slug to vrs.com:~/livery-source/<dest>/<slug>/
     where <dest> is <Aircraft> for external liveries or
     Cockpit_<Aircraft> for cockpit liveries.
     Prereq: VRS_SSH_KEY env var (private key, multiline).

  4. Trigger rebuild on vrs.com:
       python3.12 ~/bin/build-aircraft-packs.py --aircraft <Aircraft>
     Prereq: SSH key + rebuild script with --aircraft support
     deployed on vrs.com (see scripts/build-aircraft-packs.py).

  5. SCP manifest.json back, read bytes + xxhsum for <Aircraft>.
     Prereq: rebuild succeeded.

  6. Update liveries-index/<Aircraft>/pack.json locally (no commit yet).

  7. Re-run scripts/build-repo.py to regenerate the 3 manifests.

  8. SCP manifests to vrs.com (VRSInstall.xml + VRSSavedGames.xml at
     public_html/, repo.xml at Mods/).
     Prereq: SSH key.

  9. Commit + push pack.json (LAST so that if branch protection
     rejects the push, vrs.com state is still consistent and only
     the repo's pack.json drifts from main).
     Prereq: workflow has contents:write (set on the job) AND
     branch protection allows github-actions[bot] to push, OR a
     PR-based recovery is acceptable. The default GITHUB_TOKEN
     does NOT bypass branch protection -- if main requires PRs,
     the user must add github-actions[bot] to "Allow specified
     actors to bypass" or restructure to auto-PR flow.

  10. POST Discord embed to #liveries webhook.
      Prereq: DISCORD_LIVERIES_WEBHOOK env var.

If a step's prereq is missing, the script logs why and stops at that
point (or skips to Discord if reasonable). The final summary states
what ran and what was skipped.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SSH_KEY_PATH = Path("/tmp/vrs-ssh-key")
SSH_KNOWN_HOSTS = Path("/tmp/vrs-known-hosts")
EXTRACT_ROOT = Path("/tmp/livery-extract")
REMOTE_MANIFEST_LOCAL = Path("/tmp/vrs-new-manifest.json")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ----- layout parsing ------------------------------------------------


def _parse_layout(zip_path: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """Identify aircraft + slugs in the candidate zip.

    Returns (aircraft, slugs) where each slug entry is
    (dest_folder, slug_name, zip_prefix):
      - dest_folder: <Aircraft> or Cockpit_<Aircraft> (rsync destination)
      - slug_name: livery folder name
      - zip_prefix: prefix in zip to strip when extracting this slug

    Supports both layouts:
      - Single-livery upload: <Aircraft>/<slug>/...
      - Full-pack (test corpus): <Aircraft>/Liveries/<dest>/<slug>/...
        where <dest> is <Aircraft> or Cockpit_<Aircraft>.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
    if not names:
        raise ValueError("empty zip")

    tops = {n.split("/", 1)[0] for n in names if "/" in n}
    if len(tops) != 1:
        raise ValueError(f"expected one top folder, got: {sorted(tops)}")
    aircraft = next(iter(tops))

    full_pack_prefix = f"{aircraft}/Liveries/"
    is_full_pack = any(n.startswith(full_pack_prefix) for n in names)

    slugs: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()

    if is_full_pack:
        for n in names:
            parts = n.split("/")
            if (
                len(parts) < 5
                or parts[0] != aircraft
                or parts[1] != "Liveries"
            ):
                continue
            dest_folder, slug_name = parts[2], parts[3]
            if not dest_folder or not slug_name:
                continue
            key = (dest_folder, slug_name)
            if key in seen:
                continue
            seen.add(key)
            slugs.append(
                (
                    dest_folder,
                    slug_name,
                    f"{aircraft}/Liveries/{dest_folder}/{slug_name}/",
                )
            )
    else:
        for n in names:
            parts = n.split("/")
            if len(parts) < 3 or parts[0] != aircraft:
                continue
            slug_name = parts[1]
            if not slug_name:
                continue
            key = (aircraft, slug_name)
            if key in seen:
                continue
            seen.add(key)
            slugs.append((aircraft, slug_name, f"{aircraft}/{slug_name}/"))

    return aircraft, slugs


def _extract_slug(zip_path: Path, slug: tuple[str, str, str], out_dir: Path) -> int:
    """Extract one slug's content into out_dir/<slug_name>/.

    The zip_prefix is stripped. Skips any entry containing `..` as a
    defense-in-depth check (the scanner should already have rejected
    path traversal, but a publish.py that blindly trusts the scanner
    is one bug away from RCE).
    Returns the number of files written.
    """
    dest_folder, slug_name, prefix = slug
    target = out_dir / slug_name
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if not info.filename.startswith(prefix) or info.is_dir():
                continue
            rel = info.filename[len(prefix):]
            if not rel or rel.endswith("/"):
                continue
            if ".." in rel.split("/"):
                continue
            out_path = target / rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(out_path, "wb") as dst:
                shutil.copyfileobj(src, dst)
            count += 1
    return count


# ----- SSH helpers ---------------------------------------------------


def _ssh_setup() -> Path | None:
    """Materialize VRS_SSH_KEY into a temp file with 0600 perms."""
    key = os.environ.get("VRS_SSH_KEY", "").strip()
    if not key:
        return None
    if not key.endswith("\n"):
        key += "\n"
    SSH_KEY_PATH.write_text(key, encoding="utf-8")
    SSH_KEY_PATH.chmod(0o600)
    SSH_KNOWN_HOSTS.touch(exist_ok=True)
    SSH_KNOWN_HOSTS.chmod(0o600)
    return SSH_KEY_PATH


def _ssh_opts(key_path: Path) -> list[str]:
    return [
        "-i", str(key_path),
        "-o", f"UserKnownHostsFile={SSH_KNOWN_HOSTS}",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
    ]


def _ssh_exec(host: str, key_path: Path, cmd: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["ssh", *_ssh_opts(key_path), host, cmd],
        capture_output=True, text=True, timeout=timeout,
    )


def _rsync_to(local_dir: Path, host: str, remote_dir: str, key_path: Path) -> subprocess.CompletedProcess:
    ssh_e = "ssh " + " ".join(_ssh_opts(key_path))
    # vrs.com's rsync is 3.1.3, which lacks --mkpath (added in 3.2.3).
    # Create the destination tree remotely via the --rsync-path mkdir
    # idiom so it works regardless of the remote rsync version.
    rsync_path = f"mkdir -p {shlex.quote(remote_dir)} && rsync"
    return subprocess.run(
        ["rsync", "-az", "--rsync-path", rsync_path, "-e", ssh_e,
         f"{local_dir}/", f"{host}:{remote_dir}/"],
        capture_output=True, text=True, timeout=900,
    )


def _scp_to(local: Path, host: str, remote: str, key_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["scp", *_ssh_opts(key_path), str(local), f"{host}:{remote}"],
        capture_output=True, text=True, timeout=120,
    )


def _scp_from(host: str, remote: str, local: Path, key_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["scp", *_ssh_opts(key_path), f"{host}:{remote}", str(local)],
        capture_output=True, text=True, timeout=120,
    )


# ----- git, manifests, Discord --------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True
    )


def _commit_and_push(repo: Path, file_rel: str, message: str) -> tuple[bool, str]:
    actor = os.environ.get("GITHUB_ACTOR", "github-actions[bot]")
    email = f"{actor}@users.noreply.github.com"
    _git(repo, "config", "user.name", actor)
    _git(repo, "config", "user.email", email)
    _git(repo, "add", file_rel)
    diff = _git(repo, "diff", "--cached", "--name-only").stdout.strip()
    if not diff:
        return True, "no-op (pack.json unchanged)"
    commit = _git(repo, "commit", "-m", message)
    if commit.returncode != 0:
        return False, f"commit failed: {commit.stderr.strip()[:200]}"
    # Push with one rebase-retry on non-fast-forward. Serialization on the
    # cron side stops the automation racing itself, but this also covers a
    # human pushing to main mid-run or a one-tick serialization miss.
    push = _git(repo, "push", "origin", "HEAD:main")
    if push.returncode == 0:
        return True, "pushed"
    _git(repo, "fetch", "origin", "main")
    rb = _git(repo, "rebase", "origin/main")
    if rb.returncode != 0:
        _git(repo, "rebase", "--abort")
        return False, f"rebase failed (conflict?): {rb.stderr.strip()[:200]}"
    push = _git(repo, "push", "origin", "HEAD:main")
    if push.returncode != 0:
        return False, f"push failed after rebase: {push.stderr.strip()[:200]}"
    return True, "pushed (after rebase)"


def _regen_manifests(repo: Path) -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "scripts/build-repo.py"],
        cwd=repo, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return False, proc.stderr.strip()[:500]
    return True, ""


def _http_post(url: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Content-Type": "application/json",
            # Discord is behind Cloudflare, which 403s (error 1010) the
            # default urllib client signature. A real UA is required.
            "User-Agent": "VRS-Livery-Pipeline/1.0 (+https://victorromeosierra.com)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"


def _discord_embed(aircraft: str, slugs: list[tuple[str, str, str]], verdict: dict, published: bool) -> dict:
    slug_list = ", ".join(f"`{s[1]}`" for s in slugs[:10])
    if len(slugs) > 10:
        slug_list += f" _and {len(slugs) - 10} more_"
    title = "New livery published" if published else "Livery scan completed"
    color = 3066993 if published else 10070709  # green / gray
    return {
        "embeds": [{
            "title": title,
            "description": (
                f"**{aircraft}** -- by **"
                f"{os.environ.get('UPLOADER_EMAIL', 'unknown')}**"
            ),
            "color": color,
            "fields": [
                {"name": "Liveries", "value": slug_list or "_(none)_", "inline": False},
                {"name": "Sample sha256", "value": f"`{verdict['sample']['sha256'][:16]}...`", "inline": True},
                {"name": "Bytes", "value": f"{verdict['sample']['bytes']:,}", "inline": True},
            ],
            "footer": {"text": "OMM users auto-update on next launch."},
        }],
    }


def _github_summary(text: str) -> None:
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if not p:
        return
    with open(p, "a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def _emit(lines: list[str]) -> None:
    text = "\n".join(lines) + "\n"
    print(text)
    _github_summary(text)


# ----- main flow -----------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path, help="candidate livery zip")
    parser.add_argument("verdict", type=Path, help="verdict.json from scan.py")
    args = parser.parse_args(argv)

    verdict = json.loads(args.verdict.read_text(encoding="utf-8"))
    host = os.environ.get("VRS_SSH_HOST", "customdc@vrs.com")

    lines = [
        "## Publish",
        "",
        "- **Verdict:** PASS",
        f"- **Sample sha256:** `{verdict['sample']['sha256']}`",
        f"- **Sample bytes:** {verdict['sample']['bytes']:,}",
        f"- **Uploader:** {os.environ.get('UPLOADER_EMAIL', 'unknown')} "
        f"(id {os.environ.get('UPLOADER_ID', '?')})",
        f"- **Original filename:** `{os.environ.get('ORIGINAL_FILENAME', '?')}`",
        "",
    ]

    # 1. parse layout
    try:
        aircraft, slugs = _parse_layout(args.zip)
    except Exception as e:  # noqa: BLE001
        lines.append(f"- **ERROR** parsing layout: `{e}`")
        _emit(lines)
        return 1

    lines.append(f"- **Aircraft:** `{aircraft}`")
    lines.append(f"- **Slugs to publish:** {len(slugs)}")
    for dest, slug_name, _ in slugs[:20]:
        lines.append(f"  - `{dest}/{slug_name}`")
    if len(slugs) > 20:
        lines.append(f"  - _and {len(slugs) - 20} more_")
    lines.append("")

    # 2. stage extraction
    if EXTRACT_ROOT.exists():
        shutil.rmtree(EXTRACT_ROOT)
    EXTRACT_ROOT.mkdir(parents=True)
    by_dest: dict[str, list[str]] = {}
    for slug in slugs:
        dest_folder, slug_name, _prefix = slug
        n = _extract_slug(args.zip, slug, EXTRACT_ROOT / dest_folder)
        by_dest.setdefault(dest_folder, []).append(slug_name)
        if n == 0:
            lines.append(f"- WARN: no files extracted for `{dest_folder}/{slug_name}`")

    # 3. SSH key
    key_path = _ssh_setup()
    if not key_path:
        lines.append("### SSH push: **SKIPPED** (VRS_SSH_KEY not set)")
        lines.append("")
        lines.append("Steps 3-8 require the dedicated ed25519 key on vrs.com. ")
        lines.append("See PLAN.md Phase 2 starting position for the secrets checklist.")
        _emit(lines)
        return 0
    lines.append(f"- **SSH host:** `{host}`")
    lines.append("")

    # 4. rsync slugs to ~/livery-source/<dest>/<slug>/
    lines.append("### Rsync slugs to vrs.com:~/livery-source/")
    rsync_ok = True
    for dest_folder, slug_names in by_dest.items():
        local_dir = EXTRACT_ROOT / dest_folder
        remote_dir = f"livery-source/{dest_folder}"
        proc = _rsync_to(local_dir, host, remote_dir, key_path)
        if proc.returncode != 0:
            lines.append(f"- FAIL `{dest_folder}` -> `{remote_dir}` (rc={proc.returncode})")
            lines.append(f"  ```")
            lines.append(f"  {proc.stderr.strip()[:800]}")
            lines.append(f"  ```")
            rsync_ok = False
        else:
            joined = ", ".join(f"`{s}`" for s in slug_names)
            lines.append(f"- OK `{dest_folder}/`: {joined}")
    lines.append("")
    if not rsync_ok:
        _emit(lines)
        return 1

    # 5. trigger rebuild on vrs.com
    lines.append("### Rebuild on vrs.com")
    rebuild_cmd = (
        f"python3.12 ~/bin/build-aircraft-packs.py "
        f"--aircraft {aircraft} "
        f"--source ~/livery-source "
        f"--out ~/public_html/Mods/Liveries"
    )
    proc = _ssh_exec(host, key_path, rebuild_cmd, timeout=900)
    lines.append(f"- rc=`{proc.returncode}`")
    if proc.stdout.strip():
        lines.append("- stdout:")
        lines.append("  ```")
        lines.append(f"  {proc.stdout.strip()[:1500]}")
        lines.append("  ```")
    if proc.returncode != 0:
        lines.append("- stderr:")
        lines.append("  ```")
        lines.append(f"  {proc.stderr.strip()[:1500]}")
        lines.append("  ```")
        lines.append("")
        lines.append("(Likely cause: build-aircraft-packs.py on vrs.com lacks ")
        lines.append("`--aircraft` mode. Deploy the updated script from ")
        lines.append("`scripts/build-aircraft-packs.py` to `~/bin/` on vrs.com.)")
        _emit(lines)
        return 1
    lines.append("")

    # 6. fetch manifest.json
    lines.append("### Fetch new manifest.json")
    if REMOTE_MANIFEST_LOCAL.exists():
        REMOTE_MANIFEST_LOCAL.unlink()
    proc = _scp_from(host, "public_html/Mods/Liveries/manifest.json", REMOTE_MANIFEST_LOCAL, key_path)
    if proc.returncode != 0 or not REMOTE_MANIFEST_LOCAL.exists():
        lines.append(f"- FAIL: rc={proc.returncode}, {proc.stderr.strip()[:300]}")
        _emit(lines)
        return 1
    manifest = json.loads(REMOTE_MANIFEST_LOCAL.read_text(encoding="utf-8"))
    new_data = manifest.get("aircraft", {}).get(aircraft, {})
    if not new_data or "bytes" not in new_data or "xxhsum" not in new_data:
        lines.append(f"- FAIL: manifest missing entry for `{aircraft}`")
        _emit(lines)
        return 1
    new_bytes = new_data["bytes"]
    new_xxhsum = new_data["xxhsum"]
    lines.append(f"- new bytes: {new_bytes:,}")
    lines.append(f"- new xxhsum: `{new_xxhsum}`")
    lines.append("")

    # 7. update pack.json LOCALLY (no commit yet -- regen + scp first so
    #    if git push fails later, the user-visible state on vrs.com is
    #    consistent: new zip + new manifests pointing to new xxhsum. The
    #    only drift is then repo pack.json vs origin/main, recoverable
    #    by re-running with a green push or by a manual PR.
    lines.append("### Update pack.json (local)")
    pack_path = REPO_ROOT / "liveries-index" / aircraft / "pack.json"
    if not pack_path.exists():
        lines.append(f"- FAIL: `{pack_path.relative_to(REPO_ROOT)}` not found")
        _emit(lines)
        return 1
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    old_xxhsum = pack.get("xxhsum")
    pack["bytes"] = new_bytes
    pack["xxhsum"] = new_xxhsum
    pack["last_built_at"] = datetime.datetime.now(
        datetime.timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    pack_path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    lines.append(f"- xxhsum: `{old_xxhsum}` -> `{new_xxhsum}`")
    lines.append("")

    # 8. regen + scp manifests (BEFORE git push -- see ordering note above)
    lines.append("### Regenerate + deploy manifests")
    ok, err = _regen_manifests(REPO_ROOT)
    if not ok:
        lines.append(f"- build-repo.py FAIL: {err}")
        _emit(lines)
        return 1
    lines.append("- regenerated Release/{VRSInstall,VRSSavedGames,repo}.xml")
    release_dir = REPO_ROOT / "Release"
    scp_ok = True
    for local_name, remote in [
        ("VRSInstall.xml", "public_html/VRSInstall.xml"),
        ("VRSSavedGames.xml", "public_html/VRSSavedGames.xml"),
        ("repo.xml", "public_html/Mods/repo.xml"),
    ]:
        proc = _scp_to(release_dir / local_name, host, remote, key_path)
        if proc.returncode != 0:
            lines.append(f"- FAIL `{local_name}` -> `{remote}`: rc={proc.returncode}")
            scp_ok = False
        else:
            lines.append(f"- OK   `{local_name}` -> `{remote}`")
    lines.append("")

    # 9. commit + push pack.json. If branch protection rejects, the
    #    user-visible state on vrs.com is still consistent (step 8 ran);
    #    only the repo's pack.json drifts from main. The publish_failed
    #    flag below ensures the run is marked failed so the user sees it.
    lines.append("### Commit + push pack.json")
    sha_short = verdict["sample"]["sha256"][:12]
    git_ok, git_msg = _commit_and_push(
        REPO_ROOT,
        f"liveries-index/{aircraft}/pack.json",
        f"Liveries ({aircraft}): publish via scan-livery ({sha_short})",
    )
    lines.append(f"- git: {'OK' if git_ok else 'FAIL'} -- {git_msg}")
    if not git_ok:
        lines.append("")
        lines.append(
            "**Heads-up:** vrs.com state is consistent (sub-pack + "
            "manifests deployed) but the repo's `liveries-index/"
            f"{aircraft}/pack.json` is now out of sync with `main`. "
            "Recover by opening a PR with the local pack.json changes, "
            "or check branch protection on `main` (Settings -> Branches) "
            "to allow `github-actions[bot]` to bypass."
        )
    lines.append("")

    # 10. Discord embed
    lines.append("### Discord #liveries")
    webhook = os.environ.get("DISCORD_LIVERIES_WEBHOOK", "").strip()
    if not webhook:
        lines.append("- SKIPPED (DISCORD_LIVERIES_WEBHOOK not set)")
    else:
        payload = _discord_embed(aircraft, slugs, verdict, published=True)
        code, body = _http_post(webhook, payload)
        lines.append(f"- POST status: `{code}`")
        if body and code not in (200, 204):
            lines.append(f"  body: `{body[:200]}`")
    lines.append("")

    _emit(lines)
    return 0 if (scp_ok and git_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
