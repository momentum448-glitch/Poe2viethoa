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
echo Chi can POE2 dang mo de tool tim Client.txt va doc log gan nhat.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto :no_python
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP 1/3] Tao virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [SETUP 1/3] Virtual environment da san sang.
)

echo [SETUP 2/3] Kiem tra pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
if errorlevel 1 goto :fail

echo [SETUP 3/3] Cai dependencies can thiet...
".venv\Scripts\python.exe" -m pip install -r requirements-spike001.txt >nul
if errorlevel 1 goto :fail

echo.
echo [PROBE] Dang tim Client.txt...
".venv\Scripts\python.exe" -X utf8 spikes\spike001b_log_probe.py
set "RC=%errorlevel%"

for /f "delims=" %%D in ('powershell -NoProfile -Command "$d=Get-ChildItem -Directory 'diagnostics\spike001b' -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($d){$d.FullName}"') do set "LATEST=%%D"

if not defined LATEST (
  echo [ERROR] Khong co ket qua probe.
  goto :fail
)

for %%D in ("%LATEST%") do set "SESSION_NAME=%%~nxD"
set "ZIP=%CD%\QC_LOG_RESULT_%SESSION_NAME%.zip"
if exist "%ZIP%" del /q "%ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%LATEST%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :fail

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

:no_python
echo.
echo [ERROR] May chua co Python 3.10+.
echo Gui anh man hinh nay cho em, em se chuyen probe sang ban portable.
pause
exit /b 2

:fail
echo.
echo [ERROR] Probe gap loi.
echo Chup man hinh cua so nay gui cho em.
pause
exit /b 1
