param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutRoot = Join-Path $Root "diagnostics\spike001b"
$Out = Join-Path $OutRoot $Stamp
New-Item -ItemType Directory -Force -Path $Out | Out-Null

function Add-Candidate {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path
    )
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    if (-not $List.Contains($Path)) {
        $List.Add($Path)
    }
}

$processPaths = @()
try {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "PathOfExile|Path of Exile"
    }
    $processPaths = @(
        $processes |
        ForEach-Object { $_.ExecutablePath } |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
    )
} catch {
    $processPaths = @()
}

$candidates = [System.Collections.Generic.List[string]]::new()

foreach ($exe in $processPaths) {
    try {
        $dir = Split-Path -Parent $exe
        Add-Candidate $candidates (Join-Path $dir "logs\Client.txt")
        Add-Candidate $candidates (Join-Path $dir "logs\KakaoClient.txt")
        $parent = Split-Path -Parent $dir
        if ($parent) {
            Add-Candidate $candidates (Join-Path $parent "logs\Client.txt")
        }
    } catch {}
}

$user = $env:USERPROFILE
Add-Candidate $candidates (Join-Path $user "Documents\My Games\Path of Exile 2\logs\Client.txt")
Add-Candidate $candidates (Join-Path $user "Documents\My Games\Path of Exile 2\Logs\Client.txt")

foreach ($drive in @("C:","D:","E:","F:","G:")) {
    Add-Candidate $candidates "$drive\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\Program Files\Steam\steamapps\common\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\SteamLibrary\steamapps\common\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\Games\Steam\steamapps\common\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\Program Files\Grinding Gear Games\Path of Exile 2\logs\Client.txt"
    Add-Candidate $candidates "$drive\Program Files (x86)\Grinding Gear Games\logs\Client.txt"
    Add-Candidate $candidates "$drive\Program Files\Grinding Gear Games\logs\Client.txt"
}

$existing = @(
    $candidates |
    Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } |
    Sort-Object { (Get-Item -LiteralPath $_).LastWriteTime } -Descending
)

$selected = $null
if ($existing.Count -gt 0) {
    $selected = $existing[0]
}

$report = [ordered]@{
    time                     = (Get-Date).ToString("s")
    process_executable_paths = $processPaths
    selected_log             = $selected
    existing_candidates      = $existing
    checked_candidates       = @($candidates)
    status                   = if ($selected) { "FOUND" } else { "NOT_FOUND" }
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

        $maxBytes = 8MB
        $bytesToRead = [Math]::Min([int64]$maxBytes, $stream.Length)
        [void]$stream.Seek(-$bytesToRead, [System.IO.SeekOrigin]::End)

        $buffer = New-Object byte[] $bytesToRead
        $read = $stream.Read($buffer, 0, $bytesToRead)
        $tail = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $read)
    }
    finally {
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
        $lines | Where-Object {
            $_ -match 'Generating level .* area "'
        }
    )
    Set-Content -LiteralPath (Join-Path $Out "zone_hits.txt") -Value $zoneHits -Encoding UTF8

    $report.tail_bytes_read = [System.Text.Encoding]::UTF8.GetByteCount($tail)
    $report.dialogue_keyword_hit_count = $dialogueHits.Count
    $report.zone_event_count_in_tail = $zoneHits.Count
}

$reportPath = Join-Path $Out "log_probe.json"
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8

$zip = Join-Path $Root ("QC_LOG_RESULT_V4_{0}.zip" -f $Stamp)
if (Test-Path -LiteralPath $zip) {
    Remove-Item -LiteralPath $zip -Force
}

Compress-Archive -Path (Join-Path $Out "*") -DestinationPath $zip -Force

$last = Join-Path $Root "LAST_QC_RESULT.txt"
@(
    "FILE CAN GUI CHO CHATGPT:"
    $zip
    ""
    "STATUS:"
    $report.status
    ""
    "CLIENT.TXT:"
    $(if ($selected) { $selected } else { "NOT FOUND" })
) | Set-Content -LiteralPath $last -Encoding UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "  XONG"
Write-Host "============================================================"
Write-Host ""
Write-Host "STATUS:" $report.status
Write-Host "ZIP:"
Write-Host " " $zip
Write-Host ""

Start-Process explorer.exe -ArgumentList $Root
