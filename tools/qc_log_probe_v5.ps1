param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Out = Join-Path $Root ("diagnostics\spike001c\" + $Stamp)
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Add-Unique {
    param([System.Collections.Generic.List[string]]$List, [string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return }
    $v = $Value.Trim().Replace("\\", "\")
    if (-not $List.Contains($v)) { $List.Add($v) }
}

function Read-SteamLibraries {
    $roots = [System.Collections.Generic.List[string]]::new()

    foreach ($reg in @(
        "HKCU:\Software\Valve\Steam",
        "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam",
        "HKLM:\SOFTWARE\Valve\Steam"
    )) {
        try {
            $p = Get-ItemProperty -Path $reg -ErrorAction Stop
            if ($p.SteamPath) { Add-Unique $roots $p.SteamPath }
            if ($p.InstallPath) { Add-Unique $roots $p.InstallPath }
        } catch {}
    }

    foreach ($base in @($roots.ToArray())) {
        $vdf = Join-Path $base "steamapps\libraryfolders.vdf"
        if (-not (Test-Path -LiteralPath $vdf)) { continue }
        try {
            $text = Get-Content -LiteralPath $vdf -Raw -Encoding UTF8
            foreach ($m in [regex]::Matches($text, '"path"\s+"([^"]+)"')) {
                $path = $m.Groups[1].Value -replace '\\\\','\'
                Add-Unique $roots $path
            }
        } catch {}
    }
    return @($roots)
}

function Read-InstallDirFromManifest {
    param([string]$Manifest)
    try {
        $text = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8
        $m = [regex]::Match($text, '"installdir"\s+"([^"]+)"')
        if ($m.Success) { return $m.Groups[1].Value }
    } catch {}
    return $null
}

$processInfo = @()
try {
    $processInfo = @(
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match "Exile|PathOf|PoE" -or $_.CommandLine -match "Path of Exile 2|2694490"
        } |
        ForEach-Object {
            [ordered]@{
                name = $_.Name
                executable_path = $_.ExecutablePath
                command_line = $_.CommandLine
                process_id = $_.ProcessId
            }
        }
    )
} catch {}

$steamLibraries = @(Read-SteamLibraries)
$manifests = [System.Collections.Generic.List[string]]::new()
$gameDirs = [System.Collections.Generic.List[string]]::new()
$candidates = [System.Collections.Generic.List[string]]::new()

foreach ($lib in $steamLibraries) {
    $manifest = Join-Path $lib "steamapps\appmanifest_2694490.acf"
    if (Test-Path -LiteralPath $manifest) {
        Add-Unique $manifests $manifest
        $installDir = Read-InstallDirFromManifest $manifest
        if ($installDir) {
            Add-Unique $gameDirs (Join-Path $lib ("steamapps\common\" + $installDir))
        }
    }
}

foreach ($p in $processInfo) {
    if ($p.executable_path) {
        $dir = Split-Path -Parent $p.executable_path
        Add-Unique $gameDirs $dir
    }
}

foreach ($dir in @($gameDirs.ToArray())) {
    Add-Unique $candidates (Join-Path $dir "logs\Client.txt")
    Add-Unique $candidates (Join-Path $dir "Logs\Client.txt")
    Add-Unique $candidates (Join-Path $dir "Client.txt")
}

$user = $env:USERPROFILE
foreach ($p in @(
    (Join-Path $user "Documents\My Games\Path of Exile 2\logs\Client.txt"),
    (Join-Path $user "Documents\My Games\Path of Exile 2\Logs\Client.txt"),
    (Join-Path $user "Documents\My Games\Path of Exile\logs\Client.txt"),
    (Join-Path $user "Documents\My Games\Path of Exile\Logs\Client.txt")
)) { Add-Unique $candidates $p }

# Search only small user config tree for Client.txt; avoid expensive whole-drive scans.
try {
    $myGames = Join-Path $user "Documents\My Games"
    if (Test-Path -LiteralPath $myGames) {
        Get-ChildItem -LiteralPath $myGames -Filter "Client.txt" -File -Recurse -ErrorAction SilentlyContinue |
        ForEach-Object { Add-Unique $candidates $_.FullName }
    }
} catch {}

$existing = @(
    $candidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Sort-Object { (Get-Item -LiteralPath $_).LastWriteTime } -Descending
)
$selected = if ($existing.Count -gt 0) { $existing[0] } else { $null }

$report = [ordered]@{
    time = (Get-Date).ToString("s")
    status = if ($selected) { "FOUND" } else { "NOT_FOUND" }
    selected_log = $selected
    process_info = $processInfo
    steam_libraries = $steamLibraries
    poe2_manifests = @($manifests)
    game_directories = @($gameDirs)
    existing_candidates = $existing
    checked_candidates = @($candidates)
}

if ($selected) {
    $stream = $null
    try {
        $stream = [System.IO.File]::Open(
            $selected,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite
        )
        $maxBytes = 16MB
        $n = [Math]::Min([int64]$maxBytes, $stream.Length)
        [void]$stream.Seek(-$n, [System.IO.SeekOrigin]::End)
        $buffer = New-Object byte[] $n
        $read = $stream.Read($buffer, 0, $n)
        $tail = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
    } finally {
        if ($stream) { $stream.Dispose() }
    }

    Set-Content -LiteralPath (Join-Path $Out "client_tail.log") -Value $tail -Encoding UTF8
    $lines = @($tail -split "\r?\n")

    $dialogueHits = @(
        $lines | Where-Object {
            $_ -match "Renly|Phaaryl|Bloody Flowers|Riverbank|Branoc|Clearfell"
        }
    )
    Set-Content -LiteralPath (Join-Path $Out "dialogue_hits.txt") -Value $dialogueHits -Encoding UTF8

    $zoneHits = @(
        $lines | Where-Object { $_ -match 'Generating level .* area "' }
    )
    Set-Content -LiteralPath (Join-Path $Out "zone_hits.txt") -Value $zoneHits -Encoding UTF8

    $report.tail_bytes_read = [System.Text.Encoding]::UTF8.GetByteCount($tail)
    $report.dialogue_keyword_hit_count = $dialogueHits.Count
    $report.zone_event_count_in_tail = $zoneHits.Count
}

$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Out "log_probe_v5.json") -Encoding UTF8

$zip = Join-Path $Root ("QC_LOG_RESULT_V5_{0}.zip" -f $Stamp)
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip -Force

@(
    "FILE CAN GUI CHO CHATGPT:"
    $zip
    ""
    "STATUS:"
    $report.status
    ""
    "CLIENT.TXT:"
    $(if ($selected) { $selected } else { "NOT FOUND" })
) | Set-Content -LiteralPath (Join-Path $Root "LAST_QC_RESULT.txt") -Encoding UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  POE2 LOG PROBE V5 - XONG"
Write-Host "============================================================"
Write-Host "STATUS:" $report.status
Write-Host "ZIP:" $zip
Write-Host ""
Start-Process explorer.exe -ArgumentList $Root
