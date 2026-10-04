@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Phase 1 QC

echo ============================================================
echo   POE2 VIET HOA - PHASE 1 QC
echo ============================================================
echo.
echo Muc tieu:
echo   - kiem tra frame stabilizer
echo   - Windows OCR + bbox
echo   - detector dialogue
echo   - phan biet normal / inventory-open layout
echo.
echo Hay mo POE2 va dung gan NPC story.
echo Tool se chay 90 giay va tu dong tao ZIP.
echo.
pause

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto :no_python
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Tao virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)

echo [SETUP] Cai / cap nhat dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo.
echo [TEST] Chay unit tests...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :fail

echo.
echo [QC] Bat dau. Hay quay lai POE2 va noi chuyen 3-5 cau.
echo Neu tien, mo inventory trong mot phan cua hoi thoai.
echo DE TOOL TU CHAY HET 90 GIAY.
echo.

".venv\Scripts\python.exe" -X utf8 -m app.phase1_probe --seconds 90
if errorlevel 1 goto :fail

for /f "delims=" %%D in ('powershell -NoProfile -Command "$d=Get-ChildItem -Directory 'diagnostics\phase1' -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($d){$d.FullName}"') do set "LATEST=%%D"

if not defined LATEST goto :fail

for %%D in ("%LATEST%") do set "SESSION_NAME=%%~nxD"
set "ZIP=%CD%\QC_PHASE1_RESULT_%SESSION_NAME%.zip"

if exist "%ZIP%" del /q "%ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%LATEST%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :fail

> "%CD%\LAST_QC_RESULT.txt" (
  echo FILE CAN GUI CHO CHATGPT:
  echo %ZIP%
)

echo.
echo ============================================================
echo   PHASE 1 QC XONG
echo ============================================================
echo.
echo Gui file:
echo   %ZIP%
echo.
start "" explorer.exe "%CD%"
pause
exit /b 0

:no_python
echo.
echo [ERROR] Khong tim thay Python.
echo Chup man hinh nay gui cho em.
pause
exit /b 2

:fail
echo.
echo [ERROR] Phase 1 QC gap loi.
echo Chup man hinh cua so nay gui cho em.
pause
exit /b 1
