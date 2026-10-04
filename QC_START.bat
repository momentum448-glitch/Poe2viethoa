@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"

title POE2 Viet Hoa - QC Spike 001

echo ============================================================
echo   POE2 VIET HOA - QC 1 CLICK
echo ============================================================
echo.
echo Muc tieu:
echo   1. Tu chuan bi moi truong neu can
echo   2. Thu Client.txt + screenshot + OCR trong 120 giay
echo   3. Tu dong dong goi ket qua thanh QC_RESULT_*.zip
echo.
echo Trong luc test:
echo   - Mo Path of Exile 2
echo   - Noi chuyen voi 1 NPC story
echo   - Chuyen qua 3-5 cau, moi cau giu 1-2 giay
echo   - Neu tien, thu ca luc inventory dong va mo
echo.
echo Nhan phim bat ky de bat dau.
pause > nul

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if errorlevel 1 goto :no_python
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [SETUP 1/3] Tao virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
)

echo [SETUP 2/3] Kiem tra pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
if errorlevel 1 goto :fail

echo [SETUP 3/3] Kiem tra dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements-spike001.txt
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   BAT DAU QC
echo ============================================================
echo.
echo Bay gio hay quay lai POE2 va noi chuyen voi NPC.
echo Tool se tu dung sau 120 giay.
echo Neu da thu du 3-5 cau, hay DE CUA SO CHAY HET 120 GIAY de tu dong dong goi.\r\nREM Neu lo bam Ctrl+C va khong co ZIP, chay QC_PACKAGE_RESULT.bat.
echo.

".venv\Scripts\python.exe" -X utf8 spikes\spike001_signal_audit.py --seconds 120
set "RUN_RC=%errorlevel%"

echo.
echo [PACKAGE] Dang tim session QC moi nhat...

for /f "delims=" %%D in ('powershell -NoProfile -Command "$d=Get-ChildItem -Directory 'diagnostics\spike001' -ErrorAction SilentlyContinue ^| Sort-Object LastWriteTime -Descending ^| Select-Object -First 1; if($d){$d.FullName}"') do set "LATEST=%%D"

if not defined LATEST (
  echo [ERROR] Khong tim thay thu muc ket qua.
  goto :fail
)

for %%D in ("%LATEST%") do set "SESSION_NAME=%%~nxD"
set "ZIP=%CD%\QC_RESULT_%SESSION_NAME%.zip"

> "%LATEST%\SEND_TO_CHATGPT.txt" (
  echo POE2 Viet Hoa - Spike 001 QC result
  echo.
  echo Hay gui NGUYEN FILE ZIP nay vao chat du an.
  echo Khong can mo hay copy tung file ben trong.
  echo.
  echo Session: %SESSION_NAME%
)

if exist "%ZIP%" del /q "%ZIP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path '%LATEST%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   QC XONG
echo ============================================================
echo.
echo File can gui cho em:
echo   %ZIP%
echo.
echo Anh chi can KEO THA file QC_RESULT_*.zip nay vao chat.
echo Em se doc log + screenshot + OCR va chot Log-first/OCR-first/Hybrid.
echo.

explorer.exe /select,"%ZIP%"
pause
exit /b %RUN_RC%

:no_python
echo.
echo ============================================================
echo   CHUA CO PYTHON
echo ============================================================
echo.
echo May nay chua tim thay Python.
echo Can Python 3.10+ de chay ban QC source hien tai.
echo Bao em thong bao nay, em se chuyen QC sang ban portable/EXE.
echo.
pause
exit /b 2

:fail
echo.
echo ============================================================
echo   QC GAP LOI
echo ============================================================
echo.
echo Hay chup man hinh cua so nay gui cho em.
echo Em se sua script, anh khong can tu debug.
echo.
pause
exit /b 1
