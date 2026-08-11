@echo off
REM ============================================================
REM  Termify - ONE-CLICK build
REM  Double-click this. It sets everything up and leaves you a
REM  ready-to-run Termify.exe in the "dist" folder.
REM  made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Building Termify...

echo.
echo   ========================================
echo    Termify build
echo   ========================================
echo.

REM ---- 0. make sure the files we need are here ----
if not exist termify.spec goto :missing_files
if not exist entry.py goto :missing_files
if not exist requirements.txt goto :missing_files
if not exist termify\__init__.py goto :missing_files

REM ---- 1. find python ----
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :no_python
echo   [1/4] Found Python: %PY%

REM ---- 2. private environment (kept inside this folder) ----
if not exist .venv\Scripts\python.exe (
  if exist .venv rmdir /s /q .venv
  echo   [2/4] Creating a private environment...
  %PY% -m venv .venv
  if errorlevel 1 goto :venv_fail
) else (
  echo   [2/4] Using existing environment
)

set "PYP=.venv\Scripts\python.exe"

REM ---- 3. install dependencies + the builder ----
echo   [3/4] Installing dependencies (this downloads a few things)...
%PYP% -m pip install --upgrade pip
%PYP% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :pip_fail

REM ---- 4. build the exe ----
echo   [4/4] Building Termify.exe (this is the slow part - can take a few minutes)...
echo        See dist\Termify.exe when this finishes.
%PYP% -m PyInstaller --noconfirm --clean termify.spec
if errorlevel 1 goto :build_fail

REM ---- done ----
if exist dist\Termify.exe (
  echo.
  echo   ========================================
  echo    SUCCESS! Your app is ready:
  echo      %~dp0dist\Termify.exe
  echo.
  echo    You can copy that one file anywhere and
  echo    double-click it. Pin it to the taskbar!
  echo   ========================================
) else (
  echo.
  echo   The build finished but I couldn't find dist\Termify.exe.
  echo   Check the messages above.
)
echo.
pause
exit /b 0

:no_python
echo.
echo   Could not find Python.
echo   Please install Python 3.10+ from https://python.org
echo   and IMPORTANT: tick "Add python.exe to PATH" during install.
echo   Then run this file again.
echo.
pause
exit /b 1

:missing_files
echo.
echo   Some files are missing from this folder.
echo   Make sure you extracted the WHOLE zip (it should contain
echo   termify.spec, entry.py, requirements.txt and the termify folder).
echo.
pause
exit /b 1

:venv_fail
echo.
echo   Could not create the environment. Make sure Python is 3.10+.
echo.
pause
exit /b 1

:pip_fail
echo.
echo   Could not install the dependencies.
echo   Check your internet connection, then run this again.
echo.
pause
exit /b 1

:build_fail
echo.
echo   The build failed. If you see "no module named ..." above,
echo   it means a library is missing - tell me which one.
echo.
pause
exit /b 1
