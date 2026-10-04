@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   POE2 Viet Hoa - Spike 001 Setup
echo ============================================================

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [ERROR] Khong tim thay Python 3.10+.
    echo Hay cai Python, sau do chay lai file nay.
    pause
    exit /b 1
  )
  set "PY=python"
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Tao virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [1/3] Virtual environment da ton tai.
)

echo [2/3] Nang cap pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/3] Cai dependencies cho Spike 001...
".venv\Scripts\python.exe" -m pip install -r requirements-spike001.txt
if errorlevel 1 goto :fail

echo.
echo [OK] Setup xong. Chay run_spike001.bat de bat dau thu nghiem.
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup that bai. Cuon len tren de xem loi.
pause
exit /b 1
