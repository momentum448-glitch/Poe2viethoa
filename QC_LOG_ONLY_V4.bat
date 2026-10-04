@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title POE2 Viet Hoa - Log Probe V4

echo ============================================================
echo   POE2 VIET HOA - LOG PROBE V4
echo ============================================================
echo.
echo Khong can Python. Khong can .venv.
echo Chi can Path of Exile 2 dang mo.
echo.
echo Dang chay...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\qc_log_probe_v4.ps1"
set "RC=%errorlevel%"

echo.
if not "%RC%"=="0" (
  echo [ERROR] Probe V4 gap loi. Error code: %RC%
  echo Chup man hinh cua so nay gui cho em.
  echo.
  pause
  exit /b %RC%
)

echo File ZIP da duoc tao NGAY CANH file QC_LOG_ONLY_V4.bat.
echo Neu Explorer khong tu mo, xem LAST_QC_RESULT.txt.
echo.
pause
exit /b 0
