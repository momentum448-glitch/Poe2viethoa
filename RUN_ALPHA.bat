@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Local Alpha

if not exist ".venv\Scripts\python.exe" goto :setup
".venv\Scripts\python.exe" -X utf8 -m tools.alpha_setup --check >nul 2>nul
if not errorlevel 1 goto :launch

:setup
call "%~dp0SETUP_ALPHA.bat" --quiet
if errorlevel 1 exit /b 1

:launch
if not exist ".venv\Scripts\pythonw.exe" goto :console
start "" ".venv\Scripts\pythonw.exe" -X utf8 -m app.alpha_app
exit /b 0

:console
".venv\Scripts\python.exe" -X utf8 -m app.alpha_app
if errorlevel 1 pause
