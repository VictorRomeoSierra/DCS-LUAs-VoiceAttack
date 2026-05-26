# PLAN.md -- VRSMods Liveries Ingest Pipeline

Status: Phase 1 deployment in progress. See **Current session state**
below for the resume checklist.
Moved from `~/Dev/VRSInfra/planning-liveries-pipeline.md` on
2026-05-24; that path is now a thin pointer back here.

---

## Current session state (2026-05-26 ~01:00 EDT)

Phase 1 is publishing per-aircraft livery sub-packs. The first build
shipped with the wrong zip structure (top folder didn't match file
name, OMM rejected with "unknown or wrong Mod Pack architecture") and
the architecture got split into two repos so each OMM channel
targets the correct install root.

**In flight:** cPanel rebuild on vrs.com is running in the
background (`python3.12 ~/bin/build-aircraft-packs.py`). Started
~23:33 EDT 2026-05-25, ETA ~02:00 EDT 2026-05-26 (~130 min total).
At last check (~00:58 EDT) it was 14 of 22 packs done, mid-write
on Mi-24P. Process: `pgrep -af build-aircraft` on vrs.com to
check. Outputs go into `~/public_html/Mods/Liveries/<Aircraft>.zip`
+ `manifest.json` when complete.

**Architecture decisions made this session:**

- **Zip structure has an outer wrapper.** Each `<Aircraft>.zip` now
  contains `<Aircraft>/Liveries/<Aircraft>/<livery>/...` (two-layer
  wrap). The outer `<Aircraft>/` matches the file name so OMM's
  old-fashion parser is happy. After OMM strips it, the remaining
  `Liveries/<Aircraft>/...` installs relative to a generic
  `<SavedGames>/DCS/` channel target. No `ModPack.xml` needed.
- **Two repo manifests.** `build-repo.py` now emits three files:
  - `repo-install.xml` -- VRS_AutoStarts (channel target: DCS
    install root, e.g. `D:\Eagle Dynamics\DCS World`)
  - `repo-savedgames.xml` -- 22 liveries (channel target:
    `<SavedGames>/DCS/`)
  - `repo.xml` -- combined, kept for backwards compat

**Resume checklist (pick up in this order tomorrow):**

1. **Wait for cPanel rebuild to finish.** Check status:
   ```
   ssh vrs.com 'pgrep -af build-aircraft 2>/dev/null'
   ssh vrs.com 'ls -lt ~/public_html/Mods/Liveries/*.zip | head -5'
   ssh vrs.com 'cat ~/public_html/Mods/Liveries/manifest.json | head'
   ```
   If `manifest.json` mtime is current and `pgrep` returns nothing,
   the build is done.
2. **Pull manifest + refresh pack.json:**
   ```
   scp vrs.com:public_html/Mods/Liveries/manifest.json Release/manifest.json
   python scripts/update-pack-index.py Release/manifest.json
   ```
3. **Regenerate the 3 repo files:**
   ```
   python scripts/build-repo.py
   ```
4. **Deploy all 3 to vrs.com:**
   ```
   scp Release/repo-install.xml Release/repo-savedgames.xml Release/repo.xml `
       vrs.com:public_html/Mods/
   ```
5. **User's turn in OMM:**
   - First, clean up the wrong-path test files from yesterday's
     IL-76MD install attempt: `rm -rf "C:\Users\brend\Saved Games\DCS\IL-76MD"`
     (the directory at the wrong path, not the correct
     `...\Liveries\IL-76MD\`).
   - Edit the two existing channels' repo URLs:
     - VRS Install channel -> `Mods/repo-install`
     - VRS Saved Games channel -> `Mods/repo-savedgames`
   - Refresh both. Install one livery (suggest `Liveries_IL-76MD`,
     smallest at 11 MB) and confirm files appear at
     `C:\Users\brend\Saved Games\DCS\Liveries\IL-76MD\MD USSR\`
     with today's date.
6. **Commit pack.json updates + close out Phase 1.**
7. **Optional cleanup** of `~/public_html/Mods/repo.xml.pre-phase1-bak`
   on vrs.com once everything works.

**Known transient state:**
- `liveries-index/*/pack.json` -- bytes match the cPanel build
  (sizes are deterministic) but xxhsum values are from the local
  rebuild and will be replaced from the cPanel manifest in step 2.
- `Release/aircraft-packs/` -- 25 GB of locally-built zips,
  gitignored. Can delete after the cPanel deploy is verified.
- `~/public_html/Mods/repo.xml.pre-phase1-bak` on vrs.com --
  rollback safety net for the original combined manifest.

**Tools live on vrs.com today:**
- `~/bin/build-aircraft-packs.py` -- repackager (outer-wrapper variant)
- `~/bin/inject-modpack-xml.py` -- legacy fallback approach,
  unused but available
- `python3.12` -- has pip + xxhash bootstrapped via get-pip.py;
  default `python3` is 3.6 and fails on Zip64

---

> **Reading order for cold-start:** `CLAUDE.md` (this repo's
> operating manual) → this file → `scripts/build-repo.py` (the
> existing `repo.xml` generator we're extending).
>
> **Where infra/ops context lives:** anything about the broader VRS
> infrastructure -- vrs.com cPanel host facts, DCSServerBot
> configuration, the alerting/Pushover relay, host topology, SSH
> plumbing, ProjectSend account access -- lives in
> **`~/Dev/VRSInfra/`** (sibling repo). That's the canonical
> planning workspace and ops scripts repo for the VRS DCS stack;
> its `MEMORY.md` indexes per-topic memory files. When you need
> "how does X work in our setup," check there first before
> re-deriving from the code.

---

## Goal

Build an automated, scanned, fault-tolerant pipeline that turns
**ProjectSend livery uploads on `vrs.com`** into **published OMM
`repo.xml` entries** that DCS players auto-pull on next launch -- *with
a static-analysis gate that catches malicious `description.lua` before
it ever reaches another player's machine.*

Two consumer surfaces today, both kept happy:

- **OMM users** (the strategic future) get per-aircraft sub-packs via
  `repo.xml` -- auto-updates land on next OMM poll with delta-only
  re-downloads.
- **OvGME users** (legacy path) keep getting the monolithic
  `Liveries.zip` via the same publish job.

Auto Starts publishing is **already done** (releases on GitHub, see
`Build-Release.ps1`); this plan extends the same repo to also drive the
livery side.

---

## Why now

1. The current `Liveries.zip` is **9.7 GB**, hand-maintained, and
   pushed via the resumable `upload-to-vrs-web.sh` script when the
   user remembers. New squadron liveries pile up in Discord DMs and
   periodically get manually merged into the pack.

2. Liveries embed `description.lua`, which DCS loads when the livery
   is rendered **client-side**. The DCS dedicated server doesn't
   render and doesn't install the liveries pack, so the server-side
   RCE path is **not in scope** -- this is purely a downloader-side
   threat model.

   But that risk is still real: vrs.com is the distribution channel
   for everyone on OMM auto-update. A malicious `description.lua` in
   our pack lands in every subscriber's DCS process on next launch.
   The blast radius is one player per malicious livery, but since
   we're acting as a publisher rather than a personal mod folder, the
   bar for "trust this upload" is higher than what each player would
   apply individually.

3. OMM migration is the strategic direction (it auto-updates -- OvGME
   doesn't). With the current monolithic 9.7 GB pack, "auto-update"
   means "re-download 9.7 GB", which is a terrible value proposition.
   Per-aircraft sub-packs make OMM feel like the obvious upgrade.

---

## Current state (2026-05-24)

### What exists

- **Repo:** [`github.com/VictorRomeoSierra/VRSMods`](https://github.com/VictorRomeoSierra/VRSMods)
  -- already has Auto Starts + Loadouts + VoiceAttack profiles + VRS
  Server mission scripting.
- **`scripts/build-repo.py`** -- generates `Release/repo.xml`.
  Currently lists 2 mods: `VRS_AutoStarts_v1.0.0` (from GH Releases)
  and `Liveries_v1.0.0` (from `vrs.com/Mods/Liveries.zip`,
  `skip_fetch: True` with manually-computed 9.7 GB / xxhsum).
- **`Build-Release.ps1`** -- builds OvGME-format zips. Forward-slash
  paths, single top-level folder per zip (OvGME is strict).
- **OMM branding:** `scripts/branding/VRS-Logo-128.jpg`.
- **`Release/repo.xml`** is presumably already deployed to
  `https://victorromeosierra.com/Mods/repo.xml`.
- **vrs.com ProjectSend** at `/upload/` -- per-user login, files land
  in `~/public_html/upload/`. Per the upload script comments and the
  cPanel discovery snapshots in `~/Dev/VRSInfra/discovery/VRS-Web/`,
  account quota is 100 GB with ~47 GB free.

### What's missing

- No detection of new ProjectSend uploads.
- No static analysis -- a malicious upload would go undetected if
  someone merged it into Liveries.zip by hand.
- No per-aircraft granularity in `repo.xml`.
- No Discord embed on successful publish.
- No on-call alert path on rejection.

### Constraints

- vrs.com is **shared cPanel** (A2 Hosting `mi3-ss122`). LVE limits:
  200% CPU, 35 EP, 1 GB pmem, 50 nproc. No Docker. No long-running
  daemons. Cron + PHP 8.5.4 + CLI Python/Perl/Node are the toolbox.
- Inode budget: 92k of 300k used -- plenty.
- GitHub repo soft limit 1 GB / hard 5 GB; individual files capped at
  100 MB. **Liveries cannot live in the git tree.** They live on
  vrs.com; the repo only tracks **metadata + scanner + tooling**.
- GitHub ToS forbids hosting malware -- the raw upload must not be
  committed to the repo even transiently. The scanner pulls from a
  signed URL, scans in /tmp, never commits the raw blob.

---

## End-state architecture

```
┌────────────────────────┐
│ User (logged in)       │
│ uploads livery via     │
│ vrs.com/upload         │
│ (ProjectSend)          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ vrs.com cron (every 2 min, python3)            │
│  - poll tbl_files.timestamp > :watermark       │
│  - JOIN tbl_users for uploader identity        │
│  - move raw file to ~/quarantine/<sha256>/     │
│    (outside public_html, no web access)        │
│  - mint short-lived signed URL                 │
│  - call GitHub API: workflow_dispatch on       │
│    VRSMods with:                  │
│      { sha256, signed_url, uploader_email,     │
│        uploader_id, original_filename,         │
│        upload_id }                             │
│  - bump watermark                              │
└──────────┬─────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│ GitHub Actions (ephemeral ubuntu runner)       │
│                                                │
│  1. download via signed URL → /tmp             │
│  2. zip-structure checks (cheap)               │
│  3. lua-ast scan of description.lua            │
│  4. DDS header validation per texture          │
│  5. ClamAV scan                                │
│  6. heuristics: size, file count, layout       │
│                                                │
│  ── verdict ────────────────────────────────   │
└────┬─────────────────────────────────────────┬─┘
     │ PASS                                    │ FAIL
     ▼                                         ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ scp livery into vrs.com:     │   │ POST verdict back to vrs.com │
│  ~/public_html/Mods/         │   │  webhook (/livery-flag.php)  │
│    Liveries-source/          │   │  - mark in quarantine DB     │
│    <aircraft>/<slug>/        │   │  - keep raw file for review  │
│                              │   │                              │
│ Trigger build-aircraft-pack  │   │ POST Discord webhook to      │
│ on the runner:               │   │  private staff channel:      │
│  - rebuild <aircraft>.zip    │   │  @on-call uploader=X         │
│  - rebuild Liveries.zip      │   │  reasons=[lua_os_execute,    │
│    (monolithic for OvGME)    │   │   path_traversal] sha=...    │
│  - scp both to vrs.com       │   │                              │
│                              │   │ Public surface untouched.    │
│ Commit meta.yaml +           │   └──────────────────────────────┘
│  regenerate repo.xml         │
│ Push to main                 │
│                              │
│ Tag release "pack-2026.05.   │
│  24-001"; release workflow:  │
│  - regen repo.xml against    │
│    new bytes/xxhsum          │
│  - scp repo.xml to vrs.com   │
│                              │
│ Discord embed → #liveries:   │
│  livery name, aircraft,      │
│  uploader, preview thumb     │
└──────────────────────────────┘
```

---

## Component 1: ProjectSend upload detection

**Approach: DB watermark cron.** ProjectSend stores file metadata in
MySQL (`tbl_files`, `tbl_users`, `tbl_groups`, etc.). Filesystem-only
polling loses uploader identity; PHP-source hooking is fragile across
ProjectSend upgrades. The DB watermark is cheapest and most robust.

```sql
SELECT
  f.id            AS upload_id,
  f.url           AS stored_filename,
  f.original_url  AS original_filename,
  f.description,
  f.uploader,
  f.timestamp     AS uploaded_at,
  u.email         AS uploader_email,
  u.name          AS uploader_name
FROM tbl_files f
LEFT JOIN tbl_users u ON u.user = f.uploader
WHERE f.timestamp > FROM_UNIXTIME(:watermark)
  AND f.category LIKE '%livery%'    -- or a dedicated category
ORDER BY f.timestamp ASC;
```

**Watermark storage:** small JSON file at
`~/cron-state/livery-pipeline.json`, owned by the cron user. Tracks
last-seen Unix timestamp + last-seen upload_id (tie-breaker).

**Filtering:** require a ProjectSend **category** named `livery` (or
similar). Users who upload to other categories don't trigger the
pipeline. Cheap policy lever -- a non-livery upload just sits in
ProjectSend as before.

**Cron cadence:** every 2 minutes. Latency-tolerant; players don't
expect uploads to be live in seconds. LVE-friendly.

**Failure mode:** if the GH dispatch call fails, the watermark
**doesn't advance** -- the next cron tick retries. Idempotency means
duplicates are fine on the GHA side too (we'll dedupe by sha256 in
the runner).

**Identity guarantees:** ProjectSend uses per-user accounts (confirmed
in conversation 2026-05-24). Every flagged sample carries a real email
+ user.id that on-call can act on.

---

## Component 2: vrs.com → GitHub Actions dispatch

**Trigger:** GitHub API
`POST /repos/VictorRomeoSierra/VRSMods/actions/workflows/scan-livery.yml/dispatches`
with `inputs: { sha256, signed_url, uploader_email, uploader_id,
original_filename, upload_id }`.

**Auth:** fine-grained PAT (or GitHub App, cleaner long-term) with
only the `actions:write` scope on the one repo. Token stored at
`~/.vrs-pipeline-secrets/gh-token` (mode 0600), loaded by the cron.

**Quarantine layout on vrs.com:**

```
~/quarantine/                          # outside public_html
  <sha256>/
    original.zip                       # raw upload, untouched
    meta.json                          # upload_id, uploader, ts
  _signed-urls/                        # short-lived (15 min) tokens
    <token>.json -> {sha256, expires}
```

**Signed URL:** small PHP endpoint at
`~/public_html/_internal/livery-blob.php?token=<x>` that streams
`~/quarantine/<sha256>/original.zip` if the token is valid and not
expired. Path is intentionally awkward; this is not a public surface,
just a way for GHA to fetch without us setting up a presigned-S3 thing
on a host that has neither.

**Token mint** is cron-local: a UUID + 15-minute expiry, written under
`~/quarantine/_signed-urls/`. Cron also cleans up expired entries.

**On dispatch failure:** retry next cron tick. If failures persist
(e.g. GH outage), the on-call alert fires via the same Layer-2
AlertEnricher path used by everything else -- documented in
`~/Dev/VRSInfra/MEMORY.md` under `alert_enrichment_relay` (Seq →
bot `/alert/enrich` → Pushover; Signal 5a is the
bot-bootloop-resistant direct-Pushover exception).

---

## Component 3: GitHub Actions scanner

Workflow: `.github/workflows/scan-livery.yml`. Triggered on
`workflow_dispatch` from vrs.com.

```yaml
on:
  workflow_dispatch:
    inputs:
      sha256:           { required: true }
      signed_url:       { required: true }
      uploader_email:   { required: true }
      uploader_id:      { required: true }
      original_filename:{ required: true }
      upload_id:        { required: true }

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r scripts/scanner/requirements.txt
      - run: |
          curl -fsSL "${{ inputs.signed_url }}" -o /tmp/livery.zip
          actual=$(sha256sum /tmp/livery.zip | cut -d' ' -f1)
          [[ "$actual" == "${{ inputs.sha256 }}" ]] || exit 64
      - run: python scripts/scanner/scan.py /tmp/livery.zip --json > /tmp/verdict.json
      - id: verdict
        run: |
          echo "passed=$(jq -r .passed /tmp/verdict.json)" >> $GITHUB_OUTPUT
      - if: steps.verdict.outputs.passed == 'true'
        run: python scripts/scanner/publish.py /tmp/livery.zip /tmp/verdict.json
        env:
          VRS_SSH_KEY: ${{ secrets.VRS_SSH_KEY }}
          DISCORD_LIVERIES_WEBHOOK: ${{ secrets.DISCORD_LIVERIES_WEBHOOK }}
      - if: steps.verdict.outputs.passed != 'true'
        run: python scripts/scanner/reject.py /tmp/verdict.json
        env:
          DISCORD_STAFF_WEBHOOK: ${{ secrets.DISCORD_STAFF_WEBHOOK }}
          VRS_WEBHOOK_KEY:       ${{ secrets.VRS_WEBHOOK_KEY }}
```

### Scanner checks (in order, fail-fast)

| Tier | Check | Reject reason |
|---|---|---|
| 1 | Zip integrity: opens cleanly, not encrypted, no entries with `..` or absolute paths | `zip_malformed`, `zip_encrypted`, `zip_path_traversal` |
| 2 | File-type allowlist: extensions in `{.dds, .lua, .png, .jpg, .txt, .json}` and nothing else | `disallowed_extension:<ext>` |
| 3 | Size/count heuristics: total expanded ≤ 500 MB, ≤ 200 files, no single file > 100 MB | `size_bomb`, `count_bomb`, `oversized_file` |
| 4 | **Lua AST scan** of `description.lua` (see below) | `lua_disallowed_call:<name>`, `lua_parse_error` |
| 5 | DDS header validation on every `.dds` (magic `DDS ` + sane header struct) | `dds_invalid` |
| 6 | ClamAV scan (`clamscan --recursive --no-summary`) | `clamav:<signature>` |

### Lua AST scan (the load-bearing check)

`description.lua` is a pure-data file in practice -- it's a sequence
of assignments like `livery = { {"NAME", 0, "TEX", false}, ... }` and
property setters. We parse with **`luaparser`** (Python port of
luaparse) and walk the AST.

**Allowlist approach.** A description.lua is ACCEPTED only if every
node is one of:

- Literal (string, number, boolean, nil)
- Table constructor (with literal-only keys)
- Assignment to one of the known property names:
  `livery`, `name`, `country`, `countries`, `order`, `default`,
  `season`, `category`, `unit_type`, `aircraft_type` (we'll extend
  this list as we encounter legitimate uses)
- Comment

**Hard rejects (anywhere in the AST):**

- Any call expression where the callee name is in:
  `os.execute`, `os.exit`, `os.remove`, `os.rename`, `os.tmpname`,
  `io.open`, `io.popen`, `io.lines`, `io.input`, `io.output`,
  `lfs.*`, `package.loadlib`, `package.cpath`, `require`, `dofile`,
  `loadfile`, `loadstring`, `load`, `string.dump`,
  `socket.*`, `net.*`, `bit.*` (debug surface),
  `debug.*`, `getfenv`, `setfenv`, `getmetatable`, `setmetatable`,
  `rawget`, `rawset`, `rawequal`, `rawlen`,
  `coroutine.*`
- Any **method call** on names matching `os|io|lfs|package|debug|socket|net|coroutine|string`
  (catches `io:open` / `_G.io.open` / etc.)
- Any reference to `_G`, `_ENV`, `_VERSION`, `__index`, `__newindex`
- String-loaded code: `load("...")`, `loadstring("...")`
- Any function that's not a property table

**Shadowing defenses:**

- Reject any local `os = ...`, `io = ...`, etc. (attempt to confuse
  the scanner by redefining names).
- Reject any `string.dump` (bytecode emit).
- Reject any concatenation that builds a "dangerous" name dynamically
  (`("o".."s")` etc.). Heuristic: reject `loadstring`/`load` outright,
  reject any `..` operator where either side is a string-literal that
  matches a denylist substring.

**Test corpus (lives in `scripts/scanner/tests/fixtures/`):**

- `clean-livery.zip` -- the canonical happy path
- `lua-os-execute.zip` -- direct RCE attempt
- `lua-io-open.zip` -- file IO
- `lua-loadstring.zip` -- string-loaded payload
- `lua-shadow-os.zip` -- `local os = ...` rebind
- `lua-method-call.zip` -- `io:open(...)`
- `zip-path-traversal.zip` -- `..\..\..\Windows\System32\evil.dll`
- `exe-payload.zip` -- `livery.exe` sneaking in
- `dds-bomb.zip` -- DDS header claiming 50 GB texture
- `encrypted.zip` -- password-protected archive
- `clean-but-mistakenly-named.zip` -- e.g. wrong aircraft folder name (should pass scan, fail layout)
- `path-with-allowed-paren.zip` -- the `F/A-18C_hornet/` directory edge case (slash in aircraft name)

Each gets a unit test asserting accept/reject + the right reason
code. **New bypass reports add a fixture** and the scanner gets
fixed. The corpus is the regression gate.

---

## Component 4: Publish on pass

Driven by `scripts/scanner/publish.py` in the GHA runner.

### 4a. Determine target aircraft from the livery layout

DCS livery zips have a canonical shape:

```
<AircraftName>/<LiveryName>/description.lua
<AircraftName>/<LiveryName>/*.dds
```

The aircraft folder name maps to a DCS internal aircraft name (e.g.
`FA-18C_hornet`, `F-16C_50`, `Mi-24P`). If the zip's top-level
directory isn't in our known-aircraft list, reject with
`unknown_aircraft:<name>` -- forces the user to package correctly or
forces us to add to the list.

Known-aircraft list lives at `scripts/scanner/aircraft.json`:

```json
{
  "FA-18C_hornet":  { "display": "F/A-18C Hornet" },
  "F-16C_50":       { "display": "F-16C Viper" },
  "A-10C_2":        { "display": "A-10C II Tank Killer" },
  "...":            { "...": "..." }
}
```

### 4b. Slot the livery into Liveries-source/

On vrs.com:

```
~/public_html/Mods/                          # web-accessible
  Liveries/                                  # OMM per-aircraft pulls
    FA-18C_hornet.zip                        # rebuilt by pipeline
    F-16C_50.zip
    A-10C_2.zip
    ...
  Liveries.zip                               # monolithic for OvGME
  repo.xml                                   # OMM manifest

~/livery-source/                             # NOT web-accessible
  FA-18C_hornet/
    VRS-001-Norrby/                          # <slug>
      description.lua
      tex_main.dds
      meta.yaml                              # uploader, ts, sha256, version
    VRS-002-Shifty/
      ...
  F-16C_50/
    ...
```

Publish flow on the runner:

1. Unpack uploaded zip → identify `<aircraft>/<slug>`.
2. SSH/SFTP push livery files into `~/livery-source/<aircraft>/<slug>/`.
3. Write `meta.yaml`:
   ```yaml
   slug: VRS-001-Norrby
   uploader: norrby@victorromeosierra.com
   uploaded_at: 2026-05-24T08:46:00Z
   sha256: a3f9b1...
   source_upload_id: 1234   # ProjectSend's upload row
   version: 2026-05-24-a3f9b1
   ```
4. **Rebuild just `<aircraft>.zip`** by zipping the contents of
   `~/livery-source/<aircraft>/` with the OvGME-strict layout
   (forward-slash, single top-level folder, etc -- same rules as
   `Build-Release.ps1`).
5. **Rebuild `Liveries.zip`** (monolithic) from the union of all
   `~/livery-source/<aircraft>/` trees. Slow (zips 9.7 GB) but only
   has to be redone on actual changes, and the actual work is on
   vrs.com -- runner just issues the SSH command.
6. Compute byte counts + xxhsums for everything that changed.
7. Commit the new `meta.yaml` to the repo at
   `liveries-index/<aircraft>/<slug>/meta.yaml`. (The repo only stores
   the index, never the binary.)
8. Re-run `scripts/build-repo.py` to regenerate `Release/repo.xml`.
   **build-repo.py needs an extension** -- see "Required code changes"
   below.
9. Commit `Release/repo.xml`, push to main, tag a release as
   `pack-YYYY.MM.DD-NNN`.
10. Release workflow fires the existing publish path: scp
    `Release/repo.xml` to `~/public_html/Mods/repo.xml` on vrs.com.

### 4c. Discord embed to #liveries

After publish completes (i.e. release tagged + repo.xml live):

```json
{
  "embeds": [{
    "title": "New livery published: VRS-001 Norrby",
    "description": "F/A-18C Hornet -- by **Norrby**",
    "color": 3066993,
    "thumbnail": { "url": "https://victorromeosierra.com/Mods/Liveries/previews/VRS-001-Norrby.jpg" },
    "fields": [
      { "name": "Pack version", "value": "2026.05.24-001", "inline": true },
      { "name": "Aircraft",     "value": "FA-18C_hornet",  "inline": true }
    ],
    "footer": { "text": "OMM users will auto-update on next launch" }
  }]
}
```

**Preview thumbnail flow.** `publish.py` looks for
`<aircraft>/<slug>/preview.jpg` in the uploaded livery zip. If
present, it gets SCP'd to
`~/public_html/Mods/Liveries/previews/<slug>.jpg` on vrs.com and
the Discord embed's `thumbnail.url` points there. If absent, the
embed falls back to the VRS logo URL. The contributor spec (filename,
size cap, format) is in the resolved questions section above.

---

## Component 5: Reject on fail

Driven by `scripts/scanner/reject.py` in the GHA runner.

### 5a. Discord role mention to staff channel

```json
{
  "content": "<@&STAFF_ONCALL_ROLE_ID>",
  "embeds": [{
    "title": "Livery upload REJECTED",
    "description": "Static scan flagged a livery from **norrby@victorromeosierra.com**.",
    "color": 15158332,
    "fields": [
      { "name": "ProjectSend upload ID", "value": "1234",  "inline": true },
      { "name": "Original filename",     "value": "my_skin.zip", "inline": true },
      { "name": "SHA256",                "value": "`a3f9b1...`", "inline": false },
      { "name": "Reasons",
        "value": "- `lua_disallowed_call: os.execute`\n- `zip_path_traversal: ../etc/passwd`",
        "inline": false },
      { "name": "Quarantined at",        "value": "`~/quarantine/a3f9b1.../` (vrs.com)", "inline": false }
    ],
    "footer": { "text": "Action: review sample, decide whether to ban uploader and remove from ProjectSend." }
  }]
}
```

### 5b. vrs.com webhook to mark quarantine state

`POST https://victorromeosierra.com/_internal/livery-flag.php` with
HMAC-signed payload `{ sha256, verdict, reasons }`. Endpoint writes a
flag file at `~/quarantine/<sha256>/REJECTED.json` so future tooling
(or you, via SSH) can list quarantined samples.

The raw upload **stays in `~/quarantine/`** indefinitely -- it's our
forensic evidence. Cleanup is a separate cron (e.g. rotate samples
older than 90 days unless a `.keep` file exists).

### 5c. The bad uploader never sees an error message

Deliberate. ProjectSend shows the upload as successful (because it
was -- they got the file onto the server). They don't see "your
livery was rejected by static scan" because we don't want to:

1. Give them a feedback loop for crafting bypasses.
2. Tip them off that they're being watched, before staff can act.

If the user pings on Discord asking when their livery will be in the
pack, that's the cue for the on-call to handle.

---

## Required changes to existing code

### `scripts/build-repo.py`

Today: hardcoded `PACKS` list with two entries (AutoStarts +
monolithic Liveries).

Needs to become: **a tree walker** over `liveries-index/`. For each
`<aircraft>/` directory:

- Compute the aircraft sub-pack ident
  (`Liveries_<AircraftName>_<PackVersion>`).
- URL: `https://victorromeosierra.com/Mods/Liveries/<AircraftName>.zip`.
- bytes/xxhsum: read from a sidecar `liveries-index/<aircraft>/pack.yaml`
  written by the publish step (same `skip_fetch: True` pattern as
  today's monolithic entry).
- Description: aircraft display name + list of liveries (from each
  `<slug>/meta.yaml`).
- Thumbnail: VRS-Logo-128.jpg as today.

Keep:

- `VRS_AutoStarts` entry (unchanged).
- `Liveries_v1.0.0` monolithic entry (rename to
  `Liveries_Monolithic_<PackVersion>` and tag with a note in
  description -- "for OvGME users; OMM users should use the per-aircraft
  packs above for delta updates"). Eventually deprecate but keep
  during migration window.

### New files

```
VRSMods/
├── liveries-index/                       # NEW: metadata only, no binaries
│   ├── FA-18C_hornet/
│   │   ├── pack.yaml                     # bytes, xxhsum, last_built_at
│   │   └── VRS-001-Norrby/
│   │       └── meta.yaml
│   └── ...
├── scripts/
│   ├── build-repo.py                     # MODIFIED (per above)
│   └── scanner/                          # NEW
│       ├── requirements.txt
│       ├── scan.py
│       ├── publish.py
│       ├── reject.py
│       ├── checks/
│       │   ├── zip_struct.py
│       │   ├── lua_ast.py
│       │   ├── dds_header.py
│       │   ├── av.py
│       │   └── heuristics.py
│       ├── aircraft.json
│       └── tests/
│           ├── fixtures/
│           └── test_scan.py
└── .github/
    └── workflows/
        ├── scan-livery.yml               # NEW
        ├── release-on-tag.yml            # NEW (or extend existing if any)
        └── ci.yml                        # NEW -- run scanner tests on PR
```

### New on vrs.com

```
~/cron-state/livery-pipeline.json         # watermark
~/quarantine/                             # raw uploads, REJECTED markers
~/livery-source/                          # source-of-truth livery tree
~/public_html/_internal/
  livery-blob.php                         # signed-URL streaming endpoint
  livery-flag.php                         # webhook for verdicts
~/public_html/Mods/Liveries/              # per-aircraft sub-packs (NEW)
  <Aircraft>.zip
~/public_html/Mods/Liveries.zip           # monolithic (existing)
~/public_html/Mods/repo.xml               # regenerated on each publish
~/bin/livery-pipeline-cron.py             # the cron task
```

### Cron entry on vrs.com

```
*/2 * * * * /usr/bin/python3 /home/customdc/bin/livery-pipeline-cron.py >> /home/customdc/cron-state/livery-pipeline.log 2>&1
```

---

## Phasing

This is a meaty feature. Recommend three phases.

### Phase 1 -- per-aircraft publish, manual ingest (1 session)

- Restructure `~/livery-source/` on vrs.com from the existing
  `Liveries.zip` contents. Extract once, organise by aircraft.
- Extend `build-repo.py` to emit per-aircraft entries.
- Write a one-shot `build-aircraft-packs.sh` on vrs.com that zips
  each aircraft folder into `~/public_html/Mods/Liveries/<aircraft>.zip`.
- Deploy new `repo.xml`. Verify OMM clients pick up the new entries
  (test on the user's own DCS install).
- **Outcome:** OMM users now get per-aircraft delta updates for
  whatever's currently in the pack. No automation yet -- still
  hand-maintained.

### Phase 2 -- scanner + GHA, semi-automatic publish (2 sessions)

- Build scanner under `scripts/scanner/` with the test corpus.
- Land `scan-livery.yml` workflow. Initial mode:
  `workflow_dispatch` from the user's hand (not yet vrs.com cron).
- Add `publish.py` that does the SSH dance to update
  `~/livery-source/` and rebuild affected aircraft packs.
- Test end-to-end with a known-clean test livery and a known-bad
  fixture.
- **Outcome:** user can trigger a livery scan-and-publish from the
  GH Actions UI. Discord embed on success, on-call ping on reject.

### Phase 3 -- ProjectSend cron, full automation (1 session)

- ProjectSend DB watermark cron on vrs.com.
- `livery-blob.php` signed-URL endpoint.
- `livery-flag.php` webhook for verdicts.
- HMAC signing on both endpoints.
- Wire cron → workflow_dispatch.
- **Outcome:** upload-to-published is hands-off.

---

## Resolved -- Phase 1 ground (settled 2026-05-24)

1. **Aircraft canonical names.** Inventory taken from
   `vrs.com:~/public_html/Mods/Liveries.zip` (Apr 26 2026, 9.7 GB):
   - **External liveries (21):** `A-10A`, `A-4E-C`, `AV8BNA`, `CH-47F`,
     `F-16C`, `F-16C_50`, `FA-18C_hornet`, `Ka-50_3`, `M-2000C`,
     `Mi-24P`, `Mi-8MT`, `MiG-21bis`, `Su-33`, `UH-60L`, `Uh-1H`,
     `a-10c`, `a-10cII`, `f-14b`, `il-76md`, `ka-50`, `uh-60a`
   - **Cockpit liveries (8):** `Cockpit-Ka-50_3`, `Cockpit_AH-64D`,
     `Cockpit_Mi-24P`, `Cockpit_Mi-8MT`, `Cockpit_MiG-21bis`,
     `Cockpit_Su-25T`, `Cockpit_Su-33`, `Cockpit_UH-1H`
   - **Case normalization:** folders are renamed to DCS-canonical names
     in a one-shot restructuring before Phase 1 ships
     (e.g. `a-10c` -> `A-10C`, `Uh-1H` -> `UH-1H`, `f-14b` -> `F-14B`).
   - **Cockpit handling:** each `Cockpit_<Aircraft>` tree folds into
     the same per-aircraft sub-pack as the matching external
     `<Aircraft>` tree (one OMM entry per aircraft, not two). The
     build script lays them into different paths inside the zip --
     external under `Liveries/<Aircraft>/...`, cockpit under whatever
     DCS install path is correct (confirm via spot-check in
     pre-Phase-1 homework below).
   - **Duplicate folders** (`F-16C` vs `F-16C_50`, `ka-50` vs `Ka-50_3`,
     and similar) need a merge plan -- see homework below.

2. **Existing `Liveries.zip` structure.** Confirmed:
   `Liveries/<AircraftName>/<LiveryName>/...` -- one level deeper than
   the original plan diagrams showed. The wrapping `Liveries/` makes
   the monolithic zip a drop-in for `<DCS>/Saved Games/DCS/`.
   Per-aircraft sub-packs intended for OMM Saved-Games install need the
   same wrapping.

3. **Discord webhook URLs.** Both channels (`#liveries` public, staff
   on-call private) exist on the VRS Discord. User to mint webhook URLs
   as a Phase 2 prereq; repo secrets
   `DISCORD_LIVERIES_WEBHOOK` + `DISCORD_STAFF_WEBHOOK` + the on-call
   role ID get added at that point.

4. **GitHub PAT / App scope.** Fine-grained PAT scoped to
   `VictorRomeoSierra/VRSMods` with `actions:write` only. Stored at
   `~/.vrs-pipeline-secrets/gh-token` (mode 0600) on vrs.com. Rotation
   reminder: GitHub fine-grained PATs max out at 1 year.

5. **SSH key for vrs.com from GHA.** Mint a dedicated ed25519
   keypair (do not reuse `~/.ssh/Shifty`). Public key on vrs.com's
   `~/.ssh/authorized_keys` with a `command=` restriction limiting
   writes to:
   - `~/livery-source/`
   - `~/public_html/Mods/Liveries/`
   - `~/public_html/Mods/Liveries.zip`
   - `~/public_html/Mods/repo.xml`
   Private key as `VRS_SSH_KEY` repo secret. Bounds the blast radius
   if the secret leaks.

6. **OMM repo.xml size ceiling.** None found.
   `~/Dev/OpenModMan/src/OmNetRepo.cpp` parses `<references>` as a
   dynamic list -- no hardcoded max. Non-issue for any realistic VRS
   scale.

7. **Auto Starts in the same pipeline.** No. Auto Starts continues to
   flow through `git push` -> tag -> `gh release create` ->
   `build-repo.py` regen (the existing path in `Build-Release.ps1`).
   Only shared piece with the livery pipeline is the resulting
   `repo.xml`. Pipelines stay independent.

8. **Preview images on Discord embed.** User-supplied, not
   auto-extracted. Each livery includes an optional `preview.jpg`
   alongside `description.lua` in its folder; the publish flow uses
   it if present, falls back to the VRS logo otherwise.
   Contributor spec (agreed with Ryot 2026-05-24, the primary livery
   contributor):
   - Filename: `preview.jpg` (case-sensitive, lowercase)
   - Location: at the root of each `<livery>/` folder
   - Max dimensions: 256x256 (will be displayed by Discord as a
     thumbnail)
   - Max file size: ~50 KB
   - Format: JPEG, sRGB
   - Optional. Absence means logo fallback; no warning, no rejection.

   Auto-DDS-extraction was sanity-checked against five aircraft on
   2026-05-24 and rejected: ImageMagick v6 (the version on vrs.com)
   fails on BC7-compressed DDS, ~50% hit rate, and even when it works
   the result is a UV-mapped skin atlas rather than a recognizable
   aircraft thumbnail. User-supplied is strictly better.

9. **`Mods/aircraft/` collision with `liveries-index/`.** None.
   `Mods/aircraft/` is Auto Starts source under the `Mods/`
   namespace; `liveries-index/` is a new top-level directory at the
   repo root. They never overlap.

10. **Monolithic `Liveries.zip` versioning.** Drop from `repo.xml`
    entirely (only the user is on OMM today, so no migration
    concern). The pipeline still rebuilds `Liveries.zip` and ships it
    to `https://victorromeosierra.com/Mods/Liveries.zip` so legacy
    OvGME users can grab it by direct download. OMM users see only
    per-aircraft entries.

## Source-of-truth on vrs.com (confirmed 2026-05-24)

- `~/public_html/Mods/Liveries.zip` -- 9.7 GB, Apr 26 2026.
  **Authoritative.** User also has a local copy in `~/Downloads`.
- `~/public_html/Mods/Liveries.zip.bak` -- 6.7 GB, Sep 2023. Stale,
  safe to delete after Phase 1.
- `~/public_html/Mods/LiveriesUnpacked/` -- partial extraction
  (5 of 28+ aircraft), Sep 2023. Stale, safe to delete after
  Phase 1.

## Aircraft mapping & install paths (resolved 2026-05-24)

### Cockpit livery install path

Cockpit liveries install to
**`<SavedGames>/DCS/Liveries/Cockpit_<airframe>/`** -- not to
`<DCS>/CoreMods/aircraft/.../Cockpit/Liveries/` as originally
speculated. Confirmed by spot-check of the user's own Saved Games:
all 8 `Cockpit_*` folders sit side-by-side with external livery
folders under `<SavedGames>/DCS/Liveries/`. DCS routes them to the
correct cockpit using the `Cockpit_` folder-name prefix; no
elevated permissions or CoreMods modification needed.

Practical consequence -- the per-aircraft sub-pack zip layout is just

```
Liveries/
  <Aircraft>/           # external liveries
    <livery-name>/
      description.lua
      preview.jpg       # optional, used for Discord embed
      *.dds *.png ...
  Cockpit_<Aircraft>/   # cockpit liveries (if any)
    <livery-name>/
      ...
```

and OMM/OvGME extracts it as-is into `<SavedGames>/DCS/`. No special
install-path branching in the build script.

### Sub-pack inventory

22 per-aircraft sub-packs published in Phase 1, mapped from the 29
source folders in the current `Liveries.zip` (21 external + 8
cockpit):

| Sub-pack ident | External source | Cockpit source | Op |
|---|---|---|---|
| `A-10A` | `A-10A` | -- | keep |
| `A-10C` | `a-10c` | -- | case fix |
| `A-10C_2` | `a-10cII` | -- | case + DCS-canonical name fix (A-10C II) |
| `A-4E-C` | `A-4E-C` | -- | keep (community Skyhawk mod) |
| `AH-64D` | -- | `Cockpit_AH-64D` | cockpit-only (no external Apaches in pack) |
| `AV8BNA` | `AV8BNA` | -- | keep |
| `CH-47F` | `CH-47F` | -- | keep |
| `F-14B` | `f-14b` | -- | case fix |
| `F-16C_50` | `F-16C_50` + `F-16C` (merged) | -- | F-16C contents renamed into F-16C_50; F-16C dropped (user confirmed DCS-current uses F-16C_50 exclusively) |
| `FA-18C_hornet` | `FA-18C_hornet` | -- | keep |
| `IL-76MD` | `il-76md` | -- | case fix; AI cargo plane |
| `Ka-50` | `ka-50` | -- | case fix (Black Shark 2 -- distinct module from BS3) |
| `Ka-50_3` | `Ka-50_3` | `Cockpit-Ka-50_3` -> `Cockpit_Ka-50_3` | dash-to-underscore on the cockpit folder for consistency |
| `M-2000C` | `M-2000C` | -- | keep |
| `Mi-24P` | `Mi-24P` | `Cockpit_Mi-24P` | keep |
| `Mi-8MT` | `Mi-8MT` | `Cockpit_Mi-8MT` | keep -- DCS livery folder is `Mi-8MT` even though the module is "Mi-8MTV2" (confirmed via Cockpit_Mi-8MT description.lua header) |
| `MiG-21bis` | `MiG-21bis` | `Cockpit_MiG-21bis` | keep |
| `Su-25T` | -- | `Cockpit_Su-25T` | cockpit-only (free Flaming Cliffs Su-25T) |
| `Su-33` | `Su-33` | `Cockpit_Su-33` | keep |
| `UH-1H` | `Uh-1H` | `Cockpit_UH-1H` | case fix on external |
| `UH-60A` | `uh-60a` | -- | case fix (UH-60A and UH-60L are distinct model years) |
| `UH-60L` | `UH-60L` | -- | keep |

### Folder operations to perform on vrs.com

One-shot restructuring of `~/livery-source/` (extracted from the
current `Liveries.zip`) before Phase 1 publishes:

**Eight case/canonical renames** (DCS Windows is case-insensitive
so users' existing liveries are unaffected):

```
a-10c           -> A-10C
a-10cII         -> A-10C_2
Cockpit-Ka-50_3 -> Cockpit_Ka-50_3
f-14b           -> F-14B
il-76md         -> IL-76MD
ka-50           -> Ka-50
uh-60a          -> UH-60A
Uh-1H           -> UH-1H
```

**One folder merge** -- F-16C contents are moved into F-16C_50,
then the F-16C folder is removed:

```
F-16C/<livery>/  ->  F-16C_50/<livery>/
```

When merging, any livery-name collisions between F-16C and F-16C_50
get logged and resolved manually (likely outcome: the F-16C_50
version wins by default, since that's the active module path).

---

## Memory hooks worth adding when Phase 1 lands

These would go into **this repo's** Claude memory store (separate
from VRSInfra's), since they're specific to mod-pipeline work:

- `project_liveries_pipeline.md` -- where the pieces live, who owns
  what.
- `reference_omm_repo_xml.md` -- the schema, the URL conventions, the
  build-repo.py extension contract.
- `feedback_livery_scanner.md` -- any "X is a non-issue, Y is the real
  risk" rules the user articulates during build.

Operational/infra memories that already exist in VRSInfra
(`project_alert_enrichment_relay`, `reference_seq_*`,
`project_liveries_not_on_dcs_server`, etc.) should **not** be
duplicated here -- reference them from the cross-references section
above instead.

---

## Cross-references

### In this repo

- `CLAUDE.md` -- repo operating manual; release flow, OvGME packaging
  rules, OMM repo.xml schema quirks
- `scripts/build-repo.py` -- the existing manifest generator we're
  extending in Phase 1
- `Build-Release.ps1` -- OvGME-strict zip packaging rules we need to
  match in any per-aircraft pack builder

### In VRSInfra (sibling repo at `~/Dev/VRSInfra/`)

- `MEMORY.md` -- index of per-topic memory files. Particularly
  relevant for this plan:
  - `user_role.md` -- who the user is and how they collaborate
  - `project_alert_enrichment_relay.md` -- Seq → bot /alert/enrich →
    Pushover, the L2 alert path the cron-task self-failures should
    use (livery happy/sad paths use Discord directly)
  - `project_liveries_not_on_dcs_server.md` -- liveries are
    client-only; the threat model is downloader-side, not
    server-RCE-side
  - `feedback_no_credentials.md` -- secrets (GH PAT, SSH key, Discord
    webhooks, HMAC keys) load from files, never typed in conversation
  - `reference_seq_apps.md` / `reference_seq_query.md` -- the Seq
    setup if pipeline events end up shipped to Seq
- `remote-access/upload-to-vrs-web.sh` -- the existing resumable
  hand-driven mod upload script, retained for emergencies / one-shots
- `remote-access/hosts.yaml` -- VRS-Web entry has the SSH alias +
  cPanel facts
- `discovery/VRS-Web/` -- cPanel host inventory snapshots

### External

- `~/Dev/OpenModMan/` -- OMM source, look here for any undocumented
  repo.xml constraints or behavioural quirks before extending the
  manifest schema
