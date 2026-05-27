# VRSMods -- VRS DCS mod content

Custom DCS World content for players on the **Victor Romeo Sierra**
server. Published two ways:

- **OMM** (Open Mod Manager) -- the recommended installer. Subscribes to
  the VRS repository and auto-updates as new content lands.
- **OvGME** -- still supported for users not on OMM. Manual download +
  enable per release.

## What's in the pack

- **Auto Starts** -- drop-in `Macro_sequencies.lua` quick-start scripts
  for the aircraft we fly. Each one runs a consistent VRS Quick Start
  sequence on the in-game keybind.
- **Loadouts** -- shared aircraft payload definitions so everyone in
  the squadron sees the same loadouts in the Mission Editor.
- **Liveries** -- squadron and unit liveries for the airframes flown
  on VRS, distributed as a separate ~10 GB pack at
  <https://victorromeosierra.com/Mods/Liveries.zip>. An automated
  ingest + scan + publish pipeline is in progress -- see
  `~/Dev/VRSInfra/planning-liveries-pipeline.md`.
- **VRS Server** -- mission scripting building blocks (CSAR, CTLD,
  DSMC, MOOSE, Mist) for our server missions. Not packaged for
  end-user install -- this is server-side source.
- **VoiceAttack** -- VoiceAttack profiles, including the current
  `VRS AI` profile and the legacy Rotorheads-era profiles. Not
  packaged for OvGME / OMM -- copy by hand.

## Install -- OMM (recommended)

[Open Mod Manager](https://github.com/iquercorb/OpenModMan) is the
preferred installer. Unlike OvGME, OMM auto-updates from the VRS
repositories, so new liveries and mod updates land on next launch
without you re-downloading by hand.

VRS publishes **two** repositories, one per DCS install location. Add
both to OMM as separate channels:

| Channel | Install target | Repository URL |
|---|---|---|
| VRS Install | your DCS install root, e.g. `D:\DCS World OpenBeta` | `https://victorromeosierra.com/VRSInstall.xml` |
| VRS Saved Games | your DCS Saved Games root, e.g. `C:\Users\<you>\Saved Games\DCS` | `https://victorromeosierra.com/VRSSavedGames.xml` |

The split is because Auto Starts install to `<DCS install>/Mods/...`
while Liveries install to `<Saved Games>/DCS/Liveries/...` -- OMM
has one destination root per channel, so each repository targets one.

1. Install OMM. Create a Mod Hub (any name) -- this groups your
   channels together.
2. Inside the hub, create the **VRS Install** channel: install target
   = your DCS install root, repository = the `VRSInstall.xml` URL
   above.
3. Create the **VRS Saved Games** channel: install target = your
   DCS Saved Games folder, repository = the `VRSSavedGames.xml` URL.
4. In each channel, subscribe to the entries you want and install.
   OMM tracks what's installed and pulls updates on next launch.

If you prefer a single subscription (legacy behaviour), the combined
manifest at <https://victorromeosierra.com/Mods/repo.xml> lists both
sets -- but every mod still installs at one specific path, so a
single-channel setup will only work for one of the two sets.

## Install -- OvGME (legacy)

[OvGME](https://wiki.hoggitworld.com/view/OVGME) copies the mod into
your DCS install, keeps an automatic backup, and lets you toggle the
mod on/off without touching files by hand. It doesn't auto-update, so
you'll re-download zips manually when content changes.

1. Install OvGME and point its **Root** at your DCS install folder
   (e.g. `D:\DCS World OpenBeta`). Point its **Mods** folder at any
   empty directory you want to keep mod folders in.
2. Grab the latest release zips:
   - `VRS_AutoStarts.zip`
   - `VRS_Loadouts.zip`
3. Extract each zip into your OvGME **Mods** folder. You'll end up
   with `VRS_AutoStarts\` and `VRS_Loadouts\` next to each other.
4. In OvGME, enable each mod. OvGME copies files into your DCS
   install and backs up the originals.

To uninstall, disable the mod in OvGME and originals are restored.

## Building the release

From a PowerShell prompt at the repo root:

```powershell
pwsh .\Build-Release.ps1
```

The OvGME-format zips land in `Release\` (gitignored). Then to
regenerate the OMM manifest:

```powershell
python scripts\build-repo.py
```

`Release\repo.xml` is the OMM manifest -- deploy it to
`https://victorromeosierra.com/Mods/repo.xml` so clients pick it up.

## Repo layout

```
Mods\aircraft\<airframe>\Cockpit\Scripts\Macro_sequencies.lua   # source autostarts
Loadouts\Main DCS\MissionEditor\data\scripts\UnitPayloads\      # source loadouts
VoiceAttack\                                                    # VA profiles (not packaged)
VRS Server\                                                     # mission scripting (not packaged)
Build-Release.ps1                                               # OvGME zip builder
scripts\
  build-repo.py                                                 # OMM repo.xml generator
  branding\VRS-Logo-128.jpg                                     # thumbnail used in OMM
Release\                                                        # build output (gitignored)
```

See `CLAUDE.md` for cold-start orientation for future Claude Code
sessions in this repo.
