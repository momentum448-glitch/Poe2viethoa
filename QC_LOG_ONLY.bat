@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Log Probe

echo ============================================================
echo   POE2 VIET HOA - LOG PROBE
echo ============================================================
echo.
echo Probe nay KHONG can noi chuyen NPC lai.
echo Chi can POE2 dang mo de tool tim duong dan Client.txt tot hon.
echo.

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Khong tim thay .venv tu lan QC truoc.
  echo Hay chay QC_START.bat neu can.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -X utf8 spikes\spike001b_log_probe.py
set "RC=%errorlevel%"

for /f "delims=" %%D in ('powershell -NoProfile -Command "$d=Get-ChildItem -Directory 'diagnostics\spike001b' -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($d){$d.FullName}"') do set "LATEST=%%D"

if not defined LATEST (
  echo [ERROR] Khong co ket qua probe.
  pause
  exit /b 1
)

for %%D in ("%LATEST%") do set "SESSION_NAME=%%~nxD"
set "ZIP=%CD%\QC_LOG_RESULT_%SESSION_NAME%.zip"
if exist "%ZIP%" del /q "%ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%LATEST%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
  echo [ERROR] Khong tao duoc ZIP.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   XONG
echo ============================================================
echo.
echo Gui file nay cho em:
echo   %ZIP%
echo.
explorer.exe /select,"%ZIP%"
pause
exit /b %RC%
