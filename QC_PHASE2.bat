@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Phase 2 QC

echo ============================================================
echo   POE2 VIET HOA - PHASE 2 QC
echo ============================================================
echo.
echo Lan chay nay se:
echo   - test code
echo   - dong bo fresh source (cache lai cho lan sau)
echo   - build runtime translation DB
echo   - chay matcher QC 60 giay POE2 foreground
echo.
echo Nen mo POE2 va dung gan Renly hoac Una.
echo Cac topic Alpha da co ban dich:
echo   Renly: Introduction / The Miller
echo   Una:   Home / Clearfell
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
echo [SOURCE] Dong bo fresh source...
".venv\Scripts\python.exe" -X utf8 -m tools.source_sync
if errorlevel 1 goto :fail

echo.
echo [BUILD] Tao runtime translation DB...
".venv\Scripts\python.exe" -X utf8 -m tools.build_translation_db
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   BAT DAU MATCHER QC - 60 GIAY ACTIVE GAME
echo ============================================================
echo.
echo Quay lai POE2, mo mot trong cac topic Alpha o tren.
echo Co the chuyen qua lai vai cau, inventory dong/mo tuy y.
echo.
echo Luu y:
echo   - timer chi tinh khi POE2 dang foreground
echo   - neu Alt+Tab, timer tu tam dung
echo   - tool khong capture/OCR app khac
echo   - de tool chay du 60 giay active
echo.

".venv\Scripts\python.exe" -X utf8 -m app.phase2_probe --seconds 60
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   PHASE 2 QC XONG
echo ============================================================
echo.
echo Gui file QC_PHASE2_RESULT_*.zip trong thu muc nay cho em.
echo Xem LAST_QC_RESULT.txt neu can duong dan chinh xac.
echo.
start "" explorer.exe "%CD%"
pause
exit /b 0

:no_python
echo.
echo [ERROR] Khong tim thay Python 3.10+.
pause
exit /b 2

:fail
echo.
echo [ERROR] Phase 2 QC gap loi.
echo Chup man hinh cua so nay gui cho em.
pause
exit /b 1
