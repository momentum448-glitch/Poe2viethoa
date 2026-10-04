@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
title POE2 Viet Hoa - Log Probe V5

echo ============================================================
echo   POE2 VIET HOA - LOG PROBE V5
echo ============================================================
echo.
echo V5 tim game qua Steam Registry + libraryfolders.vdf
echo + appmanifest_2694490.acf, khong doan o dia nua.
echo.
echo Hay de Path of Exile 2 dang mo, sau do cho vai giay.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\qc_log_probe_v5.ps1"
set "RC=%errorlevel%"

echo.
if not "%RC%"=="0" (
  echo [ERROR] V5 gap loi. Error code: %RC%
  echo Chup man hinh cua so nay gui cho em.
  pause
  exit /b %RC%
)

echo.
echo Da tao QC_LOG_RESULT_V5_*.zip ngay trong thu muc nay.
echo Gui file ZIP do cho em.
echo.
pause
exit /b 0
