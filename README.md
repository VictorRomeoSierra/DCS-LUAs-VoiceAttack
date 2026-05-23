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
   `VRS - Auto Starts\` (and a sibling `Mi-8 Variants\` from the auto starts
   zip) and `VRS - Loadouts (Install)\` next to each other.
4. In OvGME, enable each mod. OvGME copies files into your DCS install and
   backs up the originals.

To uninstall, disable the mod in OvGME and originals are restored.

### Mi-8MTV2 variants

The Mi-8 auto start ships with the **Generic** variant by default. The
`Mi-8 Variants\` folder next to the OvGME mod contains the themed variants
(Baywatch Day, Sharon Day, Sharon Night). To swap one in, rename it to
`Macro_sequencies.lua` and copy it into
`VRS - Auto Starts\Mods\aircraft\Mi-8MTV2\Cockpit\Scripts\` **before**
enabling the mod in OvGME.

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
