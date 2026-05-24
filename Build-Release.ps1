# Build-Release.ps1
# Builds OvGME-ready release zips for the VRS DCS auto starts and loadouts.
#
# Run from the repo root:
#     pwsh .\Build-Release.ps1
#
# Outputs:
#     Release\VRS_AutoStarts.zip
#     Release\VRS_Loadouts.zip
#
# OvGME packaging rules (per reference zips in D:\Temp\Update\OvGME):
#   - Each zip contains exactly ONE top-level folder.
#   - That folder's name matches the zip filename (minus .zip).
#   - Inside the folder, the path mirrors the DCS install root.
#   - No README.txt or other extras at the top level.

$ErrorActionPreference = "Stop"

# Use .NET ZipFile (not Compress-Archive) — PS 5.1's Compress-Archive
# writes backslash path separators which violate the ZIP spec and are
# rejected by strict parsers like OvGME.
Add-Type -AssemblyName System.IO.Compression.FileSystem

function New-OvgmeZip {
    # Builds a zip matching OvGME's expected layout:
    #   - Forward-slash path entries (ZIP spec).
    #   - Single top-level folder named after SourceDir.
    #   - Explicit directory entries (trailing '/'), as OvGME requires them.
    #   - Depth-first preorder traversal: each directory entry, then its files,
    #     then recurse into subdirectories. Matches the reference OvGME zip.
    #   - No redundant entry for the top folder itself; only its children.
    # Avoids Compress-Archive and ZipFile.CreateFromDirectory; both write
    # backslash separators on Windows, which OvGME rejects.
    param([string]$SourceDir, [string]$ZipPath)
    if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
    $topName    = Split-Path $SourceDir -Leaf
    $sourceFull = (Resolve-Path $SourceDir).Path.TrimEnd('\')
    $zip        = [System.IO.Compression.ZipFile]::Open($ZipPath, 'Create')
    try {
        function Add-ZipDir($dirPath, $entryPrefix) {
            # Emit directory entry first (with trailing slash).
            [void] $script:zip.CreateEntry("$entryPrefix/")
            # Then files in this directory (sorted by name).
            Get-ChildItem -Path $dirPath -File | Sort-Object Name | ForEach-Object {
                $entryName = "$entryPrefix/$($_.Name)"
                [void] [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                    $script:zip, $_.FullName, $entryName,
                    [System.IO.Compression.CompressionLevel]::Optimal
                )
            }
            # Then recurse into subdirectories (sorted).
            Get-ChildItem -Path $dirPath -Directory | Sort-Object Name | ForEach-Object {
                Add-ZipDir $_.FullName "$entryPrefix/$($_.Name)"
            }
        }
        $script:zip = $zip
        # Walk children of SourceDir; their entries are prefixed with $topName.
        Get-ChildItem -Path $sourceFull -Directory | Sort-Object Name | ForEach-Object {
            Add-ZipDir $_.FullName "$topName/$($_.Name)"
        }
        Get-ChildItem -Path $sourceFull -File | Sort-Object Name | ForEach-Object {
            $entryName = "$topName/$($_.Name)"
            [void] [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $zip, $_.FullName, $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            )
        }
    } finally {
        $zip.Dispose()
        Remove-Variable -Name zip -Scope Script -ErrorAction SilentlyContinue
    }
}

$repoRoot   = $PSScriptRoot
$releaseDir = Join-Path $repoRoot "Release"
$stagingDir = Join-Path $releaseDir "_staging"

if (Test-Path $releaseDir) { Remove-Item $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

# ---------------------------------------------------------------------------
# VRS_AutoStarts.zip
# ---------------------------------------------------------------------------
Write-Host "Building VRS_AutoStarts..."

$autoStartsName = "VRS_AutoStarts"
$autoStartsRoot = Join-Path $stagingDir $autoStartsName
$modsTarget     = Join-Path $autoStartsRoot "Mods"
$modsSource     = Join-Path $repoRoot       "Mods"

Copy-Item $modsSource $modsTarget -Recurse

# Defensive: drop any *-orig.lua that might slip in (OvGME does backups).
Get-ChildItem $modsTarget -Recurse -Filter "*-orig.lua" | Remove-Item -Force

$autoStartsZip = Join-Path $releaseDir "$autoStartsName.zip"
New-OvgmeZip -SourceDir $autoStartsRoot -ZipPath $autoStartsZip
Write-Host "  -> $autoStartsZip"

Remove-Item $stagingDir -Recurse -Force
New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null

# ---------------------------------------------------------------------------
# VRS_Loadouts.zip
# ---------------------------------------------------------------------------
Write-Host "Building VRS_Loadouts..."

$loadoutsName   = "VRS_Loadouts"
$loadoutsRoot   = Join-Path $stagingDir $loadoutsName
$loadoutsTarget = Join-Path $loadoutsRoot "MissionEditor\data\scripts\UnitPayloads"
$loadoutsSource = Join-Path $repoRoot "Loadouts\Main DCS\MissionEditor\data\scripts\UnitPayloads"

New-Item -ItemType Directory -Path $loadoutsTarget -Force | Out-Null
Copy-Item "$loadoutsSource\*.lua" -Destination $loadoutsTarget

$loadoutsZip = Join-Path $releaseDir "$loadoutsName.zip"
New-OvgmeZip -SourceDir $loadoutsRoot -ZipPath $loadoutsZip
Write-Host "  -> $loadoutsZip"

Remove-Item $stagingDir -Recurse -Force

Write-Host "`nDone. Built:"
Get-ChildItem $releaseDir | ForEach-Object {
    Write-Host ("  {0} ({1:N1} KB)" -f $_.Name, ($_.Length / 1KB))
}
