# VRS - DCS Auto Starts, Loadouts, and Server Tools

This repo packages VRS's custom DCS World content:

- **Auto Starts** - drop-in `Macro_sequencies.lua` quick-start scripts for the
  aircraft we fly. Each one runs a consistent VRS Quick Start sequence on the
  in-game keybind.
- **Loadouts** - shared aircraft payload definitions so everyone in the
  squadron sees the same loadouts in the Mission Editor.
- **VRS Server** - mission scripting building blocks (CSAR, CTLD, DSMC, MOOSE,
  Mist) for our server missions.
- **VoiceAttack** - VoiceAttack profiles, including the current `VRS AI`
  profile and the legacy Rotorheads-era profiles.

## Install via OvGME

The Auto Starts and Loadouts are distributed as
[OvGME](https://wiki.hoggitworld.com/view/OVGME) mods. OvGME copies the mod
into your DCS install, keeps an automatic backup, and lets you toggle the mod
on/off without touching files by hand.

1. Install OvGME and point its **Root** at your DCS install folder (e.g.
   `D:\DCS World OpenBeta`). Point its **Mods** folder at any empty directory
   you want to keep mod folders in.
2. Grab the latest release zips:
   - `VRS Auto Starts.zip`
   - `VRS Loadouts (Install).zip`
3. Extract each zip into your OvGME **Mods** folder. You'll end up with
   `VRS_AutoStarts\` and `VRS_Loadouts\` next to each other.
4. In OvGME, enable each mod. OvGME copies files into your DCS install and
   backs up the originals.

To uninstall, disable the mod in OvGME and originals are restored.

## Building the release

From a PowerShell prompt at the repo root:

```powershell
pwsh .\Build-Release.ps1
```

The zips land in `Release\` (gitignored).

## Repo layout

```
Mods\aircraft\<airframe>\Cockpit\Scripts\Macro_sequencies.lua   # source autostarts
Loadouts\Main DCS\MissionEditor\data\scripts\UnitPayloads\      # source install-side loadouts
VoiceAttack\                                                    # VA profiles (not packaged)
VRS Server\                                                     # mission scripting (not packaged)
Build-Release.ps1                                               # OvGME zip builder
Release\                                                        # build output (gitignored)
```
