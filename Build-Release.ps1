# Build-Release.ps1
# Builds OvGME-ready release zips for the VRS DCS auto starts and loadouts.
#
# Run from the repo root:
#     pwsh .\Build-Release.ps1
#
# Outputs:
#     Release\VRS Auto Starts.zip
#     Release\VRS Loadouts (Install).zip

$ErrorActionPreference = "Stop"

$repoRoot   = $PSScriptRoot
$releaseDir = Join-Path $repoRoot "Release"
$stagingDir = Join-Path $releaseDir "_staging"

if (Test-Path $releaseDir) { Remove-Item $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

# ---------------------------------------------------------------------------
# VRS Auto Starts
# ---------------------------------------------------------------------------
Write-Host "Building VRS Auto Starts..."

$autoStartsRoot = Join-Path $stagingDir "VRS - Auto Starts"
$modsTarget     = Join-Path $autoStartsRoot "Mods"
$modsSource     = Join-Path $repoRoot       "Mods"

Copy-Item $modsSource $modsTarget -Recurse

# Strip the Mi-8 'Other StartUps' variants from the OvGME mod folder; they
# ship separately under Mi-8 Variants/ so pilots can swap them in deliberately.
$mi8VariantsInMod = Join-Path $modsTarget "aircraft\Mi-8MTV2\Cockpit\Scripts\Other StartUps"
if (Test-Path $mi8VariantsInMod) {
    Remove-Item $mi8VariantsInMod -Recurse -Force
}

# Defensive: drop any *-orig.lua that might slip in.
Get-ChildItem $modsTarget -Recurse -Filter "*-orig.lua" | Remove-Item -Force

# Mi-8 Variants folder (sibling of the OvGME mod folder, not part of the mod).
$variantsTarget = Join-Path $stagingDir "Mi-8 Variants"
New-Item -ItemType Directory -Path $variantsTarget -Force | Out-Null
Copy-Item "$modsSource\aircraft\Mi-8MTV2\Cockpit\Scripts\Other StartUps\*.lua" `
    -Destination $variantsTarget

$autoStartsReadme = @'
VRS Auto Starts
===============

This is an OvGME mod. Drop the 'VRS - Auto Starts' folder into your
OvGME mods directory, then enable it in OvGME for your DCS install root.

OvGME will copy the included Macro_sequencies.lua files into the matching
airframe paths inside your DCS install. OvGME backs up the original ED
files automatically; you do not need to make manual backups.

To uninstall: disable the mod in OvGME and the originals are restored.

Airframes included:
  - A-10C II
  - AH-64D
  - F/A-18C
  - Ka-50 Black Shark 3
  - Mi-8MTV2 (Generic; see Mi-8 Variants/ to swap)
  - Mi-24P
  - SA342 Gazelle
  - UH-1H Huey
'@
Set-Content -Encoding UTF8 -Path (Join-Path $autoStartsRoot "README.txt") -Value $autoStartsReadme

$variantsReadme = @'
Mi-8MTV2 Variants
=================

The Mi-8MTV2 auto start ships with the 'Generic' variant by default.
To use a themed variant instead, do this BEFORE enabling the mod in
OvGME (so OvGME backs up the correct original file):

  1. Pick one of the .lua files in this folder.
  2. Rename your chosen file to 'Macro_sequencies.lua'.
  3. Copy it into:
     VRS - Auto Starts\Mods\aircraft\Mi-8MTV2\Cockpit\Scripts\
     (overwriting the existing Macro_sequencies.lua there)
  4. Enable the mod in OvGME.

Variants available:
  - Macro_sequencies - Generic.lua          (default)
  - Macro_sequencies - Baywatch - DAY.lua
  - Macro_sequencies - Sharon - Day.lua
  - Macro_sequencies - Sharon - Night.lua
'@
Set-Content -Encoding UTF8 -Path (Join-Path $variantsTarget "README.txt") -Value $variantsReadme

$autoStartsZip = Join-Path $releaseDir "VRS Auto Starts.zip"
Compress-Archive -Path $autoStartsRoot, $variantsTarget -DestinationPath $autoStartsZip -Force
Write-Host "  -> $autoStartsZip"

Remove-Item $stagingDir -Recurse -Force
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

# ---------------------------------------------------------------------------
# VRS Loadouts (Install)
# ---------------------------------------------------------------------------
Write-Host "Building VRS Loadouts (Install)..."

$loadoutsRoot   = Join-Path $stagingDir "VRS - Loadouts (Install)"
$loadoutsTarget = Join-Path $loadoutsRoot "MissionEditor\data\scripts\UnitPayloads"
$loadoutsSource = Join-Path $repoRoot "Loadouts\Main DCS\MissionEditor\data\scripts\UnitPayloads"

New-Item -ItemType Directory -Path $loadoutsTarget -Force | Out-Null
Copy-Item "$loadoutsSource\*.lua" -Destination $loadoutsTarget

$includedAirframes = (Get-ChildItem $loadoutsSource -Filter *.lua |
    ForEach-Object { "  - $($_.BaseName)" }) -join "`n"

$loadoutsReadme = @"
VRS Loadouts (Install)
======================

This is an OvGME mod containing aircraft payload definitions targeted at
the DCS install directory's MissionEditor tree.

Drop the 'VRS - Loadouts (Install)' folder into your OvGME mods
directory and enable it in OvGME against your DCS install root.

OvGME will place the .lua files at:
  <DCS install>\MissionEditor\data\scripts\UnitPayloads\

Airframes included:
$includedAirframes
"@
Set-Content -Encoding UTF8 -Path (Join-Path $loadoutsRoot "README.txt") -Value $loadoutsReadme

$loadoutsZip = Join-Path $releaseDir "VRS Loadouts (Install).zip"
Compress-Archive -Path $loadoutsRoot -DestinationPath $loadoutsZip -Force
Write-Host "  -> $loadoutsZip"

Remove-Item $stagingDir -Recurse -Force

Write-Host "`nDone. Built:"
Get-ChildItem $releaseDir | ForEach-Object {
    Write-Host ("  {0} ({1:N1} KB)" -f $_.Name, ($_.Length / 1KB))
}
