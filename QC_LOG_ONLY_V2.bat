@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Log Probe V2

echo ============================================================
echo   POE2 VIET HOA - LOG PROBE V2
echo ============================================================
echo.
echo Khong can Python. Khong can .venv.
echo Chi can Path of Exile 2 dang mo.
echo.

set "OUTROOT=%CD%\diagnostics\spike001b"
for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%T"
set "OUT=%OUTROOT%\%STAMP%"
mkdir "%OUT%" >nul 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$ErrorActionPreference='SilentlyContinue';" ^
"$out='%OUT%';" ^
"$proc=Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'PathOfExile|Path of Exile' };" ^
"$exe=@($proc | ForEach-Object { $_.ExecutablePath } | Where-Object { $_ });" ^
"$c=@();" ^
"foreach($e in $exe){$d=Split-Path $e; $c += (Join-Path $d 'logs\Client.txt'); $c += (Join-Path (Split-Path $d) 'logs\Client.txt')};" ^
"$u=$env:USERPROFILE;" ^
"$c += (Join-Path $u 'Documents\My Games\Path of Exile 2\logs\Client.txt');" ^
"$drives='C:','D:','E:','F:','G:';" ^
"foreach($dr in $drives){" ^
" $c += "$dr\Program Files (x86)\Steam\steamapps\common\Path of Exile 2\logs\Client.txt";" ^
" $c += "$dr\Program Files\Steam\steamapps\common\Path of Exile 2\logs\Client.txt";" ^
" $c += "$dr\SteamLibrary\steamapps\common\Path of Exile 2\logs\Client.txt";" ^
" $c += "$dr\Program Files (x86)\Grinding Gear Games\Path of Exile 2\logs\Client.txt";" ^
" $c += "$dr\Program Files\Grinding Gear Games\Path of Exile 2\logs\Client.txt";" ^
"};" ^
"$c=$c | Select-Object -Unique;" ^
"$existing=@($c | Where-Object { Test-Path $_ } | Sort-Object { (Get-Item $_).LastWriteTime } -Descending);" ^
"$selected=if($existing.Count){$existing[0]}else{$null};" ^
"$report=[ordered]@{time=(Get-Date).ToString('s'); process_executable_paths=$exe; selected_log=$selected; existing_candidates=$existing; checked_candidates=$c};" ^
"if($selected){" ^
" $fi=Get-Item $selected; $fs=[IO.File]::Open($selected,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite);" ^
" try{$n=[Math]::Min(8388608,$fs.Length); $fs.Seek(-$n,[IO.SeekOrigin]::End)|Out-Null; $buf=New-Object byte[] $n; $read=$fs.Read($buf,0,$n); $tail=[Text.Encoding]::UTF8.GetString($buf,0,$read)}finally{$fs.Close()};" ^
" $tail | Set-Content -LiteralPath (Join-Path $out 'client_tail.log') -Encoding UTF8;" ^
" $hits=@($tail -split "`r?`n" | Where-Object { $_ -match 'Renly|Phaaryl|Bloody Flowers|Riverbank|Branoc|Clearfell' });" ^
" $hits | Set-Content -LiteralPath (Join-Path $out 'dialogue_hits.txt') -Encoding UTF8;" ^
" $zones=@($tail -split "`r?`n" | Where-Object { $_ -match 'Generating level .* area "' });" ^
" $zones | Set-Content -LiteralPath (Join-Path $out 'zone_hits.txt') -Encoding UTF8;" ^
" $report.tail_bytes_read=[Text.Encoding]::UTF8.GetByteCount($tail); $report.dialogue_keyword_hit_count=$hits.Count; $report.zone_event_count_in_tail=$zones.Count" ^
"};" ^
"$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $out 'log_probe.json') -Encoding UTF8;" ^
"if($selected){exit 0}else{exit 2}"
set "RC=%errorlevel%"

set "ZIP=%CD%\QC_LOG_RESULT_V2_%STAMP%.zip"
if exist "%ZIP%" del /q "%ZIP%" >nul 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%OUT%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   XONG
echo ============================================================
echo.
if "%RC%"=="0" (
  echo Da tim thay Client.txt va dong goi ket qua.
) else (
  echo Chua tim thay Client.txt, nhung van da dong goi bao cao tim kiem.
)
echo.
echo Gui file nay cho em:
echo   %ZIP%
echo.
explorer.exe /select,"%ZIP%"
pause
exit /b 0

:fail
echo.
echo [ERROR] Khong tao duoc file ZIP.
echo Chup man hinh nay gui cho em.
pause
exit /b 1
