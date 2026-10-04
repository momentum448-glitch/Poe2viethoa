@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Chua setup. Hay chay setup_spike001.bat truoc.
  pause
  exit /b 1
)

echo ============================================================
echo   POE2 Viet Hoa - Spike 001 Signal Audit
echo ============================================================
echo.
echo Mo POE2, sau do noi chuyen voi mot NPC co story dialogue.
echo Test se tu dung sau 120 giay. Co the nhan Ctrl+C de dung som.
echo.

".venv\Scripts\python.exe" -X utf8 spikes\spike001_signal_audit.py --seconds 120

echo.
echo Test da ket thuc. Ket qua nam trong diagnostics\spike001\
pause
