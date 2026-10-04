@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Fresh Source Sync

echo ============================================================
echo   POE2 VIET HOA - FRESH SOURCE SYNC
echo ============================================================
echo.
echo Cong viec:
echo   1. Tai source English da pin tu upstream public
echo   2. Tai transcript PoE2 hien tai de bo sung speaker/topic
echo   3. Tach ^<continue^> thanh tung segment hien tren man hinh
echo   4. Tao corpus LOCAL trong source_data (khong commit Git)
echo   5. Join voi ban dich Viet cua du an
echo   6. Build runtime	ranslations.sqlite3
echo.
echo Lan dau co the mat vai phut tuy mang.
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
echo [SYNC] Dong bo source moi...
".venv\Scripts\python.exe" -X utf8 -m tools.source_sync
if errorlevel 1 goto :fail

echo.
echo [BUILD] Tao runtime translation DB...
".venv\Scripts\python.exe" -X utf8 -m tools.build_translation_db
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo   SOURCE SYNC XONG
echo ============================================================
echo.
echo Bao cao:
echo   source_data\source_sync_report.json
echo Runtime DB:
echo   runtime\translations.sqlite3
echo.
pause
exit /b 0

:no_python
echo.
echo [ERROR] Khong tim thay Python 3.10+.
pause
exit /b 2

:fail
echo.
echo [ERROR] Source sync gap loi.
echo Chup man hinh cua so nay gui cho em.
pause
exit /b 1
