@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Phase 3 Overlay QC

echo ============================================================
echo   POE2 VIET HOA - PHASE 3 REPLACEMENT OVERLAY QC
echo ============================================================
echo.
echo Lan chay nay se:
echo   - test code
echo   - dong bo fresh source
echo   - build runtime translation DB
echo   - hien overlay Viet khi matcher High
echo   - chay QC 60 giay active trong POE2
echo.
echo Topic Alpha nen test:
echo   Renly: Introduction / The Miller
echo   Una:   Home / Clearfell
echo.
echo Overlay la click-through, khong bam/tuong tac voi game.
echo Alt+Tab se an overlay va tam dung timer.
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
echo   BAT DAU OVERLAY QC - 60 GIAY ACTIVE GAME
echo ============================================================
echo.
echo Quay lai POE2 va mo topic Alpha.
echo Neu match thanh cong, anh se thay chu Viet thay cho chu Anh.
echo Tool se tu an overlay khi Alt+Tab.
echo.

if exist "LAST_QC_RESULT.txt" del "LAST_QC_RESULT.txt"
".venv\Scripts\python.exe" -X utf8 -m app.phase3_probe --seconds 60
if errorlevel 1 goto :probe_fail

echo.
echo ============================================================
echo   PHASE 3 QC XONG
echo ============================================================
echo.
echo Gui file QC_PHASE3_RESULT_*.zip trong thu muc nay cho em.
echo Xem LAST_QC_RESULT.txt neu can duong dan chinh xac.
echo.
start "" explorer.exe "%CD%"
pause
exit /b 0

:probe_fail
echo.
echo [ERROR] Phase 3 QC dung som hoac gap loi.
if exist "LAST_QC_RESULT.txt" (
  type "LAST_QC_RESULT.txt"
  echo Gui file ZIP tren cho em de kiem tra loi.
  start "" explorer.exe "%CD%"
) else (
  echo Chup man hinh cua so nay gui cho em.
)
pause
exit /b 1

:no_python
echo.
echo [ERROR] Khong tim thay Python 3.10+.
pause
exit /b 2

:fail
echo.
echo [ERROR] Phase 3 QC gap loi.
echo Chup man hinh cua so nay gui cho em.
pause
exit /b 1
