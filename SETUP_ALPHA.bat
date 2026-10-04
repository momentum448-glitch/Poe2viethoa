@echo off
chcp 65001 > nul
setlocal EnableExtensions
cd /d "%~dp0"
title POE2 Viet Hoa - Thiet lap Alpha

echo POE2 VIET HOA - THIET LAP LOCAL ALPHA
echo Lan dau can mang de cai thu vien va tai nguon da pin.
echo Sau khi thiet lap, ban choi chay offline.
echo.

if exist ".venv\Scripts\python.exe" goto :prepare
where py >nul 2>nul
if errorlevel 1 goto :plain_python
py -3.12 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if errorlevel 1 (
  set "ALPHA_PY=py -3"
) else (
  set "ALPHA_PY=py -3.12"
)
goto :create_env

:plain_python
where python >nul 2>nul
if errorlevel 1 goto :no_python
set "ALPHA_PY=python"

:create_env
%ALPHA_PY% -c "import sys; assert sys.version_info >= (3,10)" >nul 2>nul
if errorlevel 1 goto :no_python
%ALPHA_PY% -m venv .venv
if errorlevel 1 goto :fail

:prepare
".venv\Scripts\python.exe" -X utf8 -m tools.alpha_setup
if errorlevel 1 goto :fail
if /i "%~1"=="--quiet" exit /b 0
echo.
echo Xong. Mo RUN_ALPHA.bat de choi hoac QC.
pause
exit /b 0

:no_python
echo [ERROR] Can Python 3.10+; ban da QC dung Python 3.12.
echo Cai Python cho Windows, sau do mo lai RUN_ALPHA.bat.
pause
exit /b 2

:fail
echo.
echo [ERROR] Chua thiet lap duoc. Chup cua so nay gui cho em.
pause
exit /b 1
