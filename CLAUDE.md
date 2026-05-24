# CLAUDE.md -- VRSMods cold-start orientation

Custom DCS World mod content for the **Victor Romeo Sierra** server,
distributed to players via **OMM** (Open Mod Manager, the strategic
path) and **OvGME** (legacy). Sibling repos:

- `~/Dev/VRSInfra/` -- planning workspace + shared ops scripts. **The
  in-progress livery ingest/scan/publish pipeline plan lives at
  `~/Dev/VRSInfra/planning-liveries-pipeline.md`** -- read that before
  touching anything livery-adjacent.
- `~/Dev/VRSWiki/` -- the MediaWiki overhaul at
  <https://victorromeosierra.com>.
- `~/Dev/DCS-Statistics-Dashboard/` -- the stats site on the Mac.
- `~/Dev/OpenModMan/` -- vendor source for OMM (read-only reference,
  for understanding `repo.xml` consumer behaviour).

This repo was renamed from `DCS-LUAs-VoiceAttack` to `VRSMods` on
2026-05-24. GitHub redirects cover stale URLs for the moment, but
prefer the new name in any new code or docs.

---

## What's in this repo

```
VRSMods/
  README.md                   # user-facing install + build guide
  CLAUDE.md                   # you are here
  Build-Release.ps1           # OvGME zip builder (Auto Starts + Loadouts)
  LICENSE
  Mods/aircraft/<airframe>/Cockpit/Scripts/
    Macro_sequencies.lua      # SOURCE for VRS_AutoStarts.zip
  Loadouts/Main DCS/MissionEditor/data/scripts/UnitPayloads/
    *.lua                     # SOURCE for VRS_Loadouts.zip
  VoiceAttack/                # VA profiles (Attack/Gazelle/Transport RH + VRS AI). Not packaged.
  VRS Server/                 # mission scripting building blocks (CSAR, CTLD, DSMC, Mist, Moose). Server-side source.
  scripts/
    build-repo.py             # generates Release/repo.xml (OMM manifest)
    branding/VRS-Logo-128.jpg # thumbnail used in OMM entries
  Release/                    # gitignored build output (zips + repo.xml)
  .claude/settings.local.json # gitignored (per-user)
```

The repo holds **source**. Built artifacts (zips, repo.xml) live in
`Release/` locally and are published to:

- GitHub Releases on this repo (the small Auto Starts / Loadouts zips)
- `https://victorromeosierra.com/Mods/Liveries.zip` (the 9.7 GB livery
  pack -- too big for GitHub; lives on the cPanel host directly)
- `https://victorromeosierra.com/Mods/repo.xml` (the OMM manifest --
  what OMM clients poll)

---

## Distribution surfaces

| Surface | URL | Who consumes |
|---|---|---|
| OMM manifest | `https://victorromeosierra.com/Mods/repo.xml` | OMM clients (auto-update) |
| Liveries pack | `https://victorromeosierra.com/Mods/Liveries.zip` | OMM + OvGME |
| Auto Starts zip | `https://github.com/VictorRomeoSierra/VRSMods/releases/latest/download/VRS_AutoStarts.zip` | OMM + OvGME |
| Loadouts zip | `https://github.com/VictorRomeoSierra/VRSMods/releases/latest/download/VRS_Loadouts.zip` | OMM + OvGME (where wired) |

`build-repo.py` is the source of truth for what's in `repo.xml`. It
takes the `PACKS` list, streams each URL to compute byte count +
xxhash-64, and emits `Release/repo.xml`. For the Liveries entry it
uses `skip_fetch: True` with hand-supplied bytes/xxhsum (recomputed
on vrs.com when the pack changes -- the one-liner is in the docstring).

---

## Release flow

### Auto Starts / Loadouts (small, GitHub-hosted)

```powershell
# 1. Build the OvGME-format zips
pwsh .\Build-Release.ps1

# 2. Regenerate the OMM manifest with current hashes
python scripts\build-repo.py

# 3. Tag + push
git tag autostarts-vX.Y.Z
git push origin autostarts-vX.Y.Z

# 4. Cut the GitHub Release with the zips attached
gh release create autostarts-vX.Y.Z `
  Release\VRS_AutoStarts.zip `
  Release\VRS_Loadouts.zip `
  --title "VRS Auto Starts vX.Y.Z" `
  --notes "..."

# 5. Deploy the new repo.xml to vrs.com
scp Release\repo.xml vrs.com:public_html/Mods/repo.xml
```

### Liveries (large, vrs.com-hosted)

Today: manual. Hand-merge new livery into the pack, rebuild
`Liveries.zip`, upload via `~/Dev/VRSInfra/remote-access/upload-to-vrs-web.sh`,
recompute xxhsum on vrs.com, update `PACKS` in `build-repo.py`,
regenerate + deploy `repo.xml`.

Future: automated end-to-end ingest from ProjectSend uploads with a
GHA-side static scanner. **See
`~/Dev/VRSInfra/planning-liveries-pipeline.md`**. Don't extend the
livery side without reading it first; multiple architectural decisions
already pinned down there (per-aircraft sub-pack model, scanner runs
on GHA, OMM is the strategic consumer).

---

## OvGME packaging rules (strict)

From `Build-Release.ps1` comments -- OvGME parses zips strictly:

- Each zip contains **exactly one** top-level folder.
- That folder's name matches the zip filename (minus `.zip`).
- Inside the folder, the path mirrors the DCS install root.
- **Forward-slash** path separators (PowerShell's `Compress-Archive`
  writes backslashes on Windows; the script uses `System.IO.Compression`
  directly to avoid this).
- Explicit directory entries (trailing `/`) -- OvGME requires them.
- No README.txt or other extras at the top level.

Test layout with a known-working OvGME reference zip before changing
the build script.

---

## OMM repo.xml schema (from existing `build-repo.py`)

```xml
<Open_Mod_Manager_Repository>
  <uuid>...</uuid>
  <title>VRS DCS Mods</title>
  <downpath>files/</downpath>
  <references count="N">
    <mod ident="..." file="..." bytes="..." xxhsum="..." category="VRS">
      <url>https://...</url>
      <thumbnail>data:image/jpeg;base64,...</thumbnail>
      <description bytes="N">data:application/octet-stream;base64,...</description>
    </mod>
    ...
  </references>
</Open_Mod_Manager_Repository>
```

Quirks worth knowing:

- `xxhsum` is xxhash3-64, hex-encoded.
- `<thumbnail>` is a base64 JPEG DataURI.
- `<description>` is **zlib-deflated** UTF-8 text then base64. The
  `bytes` attribute is the *uncompressed* size (OMM uses it to size
  the inflate buffer).
- `bytes` on `<mod>` is the file size from the URL, used to verify
  the download.
- `ident` MUST be unique across the manifest.

---

## Conventions

- **Commit messages**: title-case, concise, occasionally with a
  context prefix (`VRS Auto Starts: ...`). See `git log` for prior
  style.
- **Co-Authored-By trailer**: I add it when committing on the user's
  behalf; the repo's prior history doesn't use it, so it's not
  load-bearing if you want to strip.
- **No em-dashes in external-facing output** (issue bodies, PR
  descriptions, Discord posts). Use hyphens. Internal docs (like
  this one) use em-dashes freely. From
  `~/Dev/VRSInfra/session-diary/2026-05-23.md`.
- **Branches**: `main` is the published branch. `dev` exists for
  in-flight work; PRs merge `dev` -> `main`.

---

## Common pitfalls

- **`Compress-Archive` writes backslashes.** Don't use it for OvGME
  zips. The build script uses `System.IO.Compression.ZipFile` directly.
- **`Release/` is gitignored.** Don't commit built zips or
  `repo.xml`. The release flow tags and uploads them via `gh release
  create` instead.
- **xxhsum recompute on Liveries.zip** is manual today. After any
  livery change, run the one-liner from `build-repo.py`'s docstring
  on vrs.com and paste the new value into `PACKS`. (The future
  pipeline will automate this.)
- **The dormant `Liveries` repo on the org was deleted on 2026-05-24.**
  If you find references to `github.com/VictorRomeoSierra/Liveries`,
  they're stale.
- **The repo was renamed `DCS-LUAs-VoiceAttack` -> `VRSMods`** on
  2026-05-24. References to the old name in your training are stale;
  use the new name.

---

## Cross-references

- `~/Dev/VRSInfra/planning-liveries-pipeline.md` -- the livery ingest
  pipeline design
- `~/Dev/VRSInfra/remote-access/upload-to-vrs-web.sh` -- the
  resumable hand-upload to vrs.com
- `~/Dev/VRSInfra/remote-access/hosts.yaml` -- VRS-Web entry has the
  SSH alias + cPanel facts
- `~/Dev/VRSInfra/MEMORY.md` (loaded into Claude context
  automatically) -- check there for related memory entries before
  re-deriving facts
