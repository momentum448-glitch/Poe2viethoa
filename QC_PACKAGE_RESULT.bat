@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo   POE2 VIET HOA - PACKAGE LATEST QC RESULT
echo ============================================================
echo.

if not exist "diagnostics\spike001" (
  echo [ERROR] Khong tim thay diagnostics\spike001
  echo Co ve lan QC truoc chua tao du lieu.
  echo.
  pause
  exit /b 1
)

for /f "delims=" %%D in ('powershell -NoProfile -Command "$d=Get-ChildItem -Directory 'diagnostics\spike001' -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($d){$d.FullName}"') do set "LATEST=%%D"

if not defined LATEST (
  echo [ERROR] Khong tim thay session QC nao.
  pause
  exit /b 1
)

for %%D in ("%LATEST%") do set "SESSION_NAME=%%~nxD"
set "ZIP=%CD%\QC_RESULT_%SESSION_NAME%.zip"

> "%LATEST%\SEND_TO_CHATGPT.txt" (
  echo POE2 Viet Hoa - Spike 001 QC result
  echo Session: %SESSION_NAME%
  echo Gui nguyen file ZIP nay vao chat.
)

if exist "%ZIP%" del /q "%ZIP%"

echo [PACKAGE] Dang nen session:
echo   %LATEST%
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%LATEST%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
  echo [ERROR] Khong the tao ZIP.
  pause
  exit /b 1
)

echo.
echo [OK] Da tao:
echo   %ZIP%
echo.
explorer.exe /select,"%ZIP%"
pause
exit /b 0
