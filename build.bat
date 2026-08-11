@echo off
REM ============================================================
REM  Termify - ONE-CLICK build
REM  Double-click this. It sets everything up, downloads what it
REM  needs, and leaves you a ready-to-run Termify.exe in dist\.
REM  made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Building Termify...

echo.
echo   Welcome! I'm going to build Termify for you.
echo   This takes a few minutes the first time. Hang tight.
echo.

REM ---- 1. find python ----
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo   Could not find Python.
  echo   Install Python 3.10+ from https://python.org  (tick "Add to PATH")
  echo   then run this again.
  pause
  exit /b 1
)

REM ---- 2. private environment (kept inside this folder) ----
if not exist .venv (
  echo   [1/4] Creating a private environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo   Could not create the environment. Make sure Python is 3.10+.
    pause
    exit /b 1
  )
) else (
  echo   [1/4] Using existing environment
)

set "PYP=.venv\Scripts\python.exe"

REM ---- 3. install dependencies + the builder ----
echo   [2/4] Installing dependencies (downloads a few things)...
%PYP% -m pip install --quiet --upgrade pip
%PYP% -m pip install --quiet -r requirements.txt pyinstaller
if errorlevel 1 (
  echo   Could not install dependencies. Check your internet and retry.
  pause
  exit /b 1
)

REM ---- 4. build the exe ----
echo   [3/4] Building Termify.exe (this is the slow part)...
%PYP% -m PyInstaller --noconfirm --clean termify.spec
if errorlevel 1 (
  echo   Build failed. See the messages above.
  pause
  exit /b 1
)

REM ---- 5. done ----
echo   [4/4] Done!
echo.
echo   Your app is ready:
echo     dist\Termify.exe
echo.
echo   You can copy Termify.exe anywhere and just double-click it.
echo   Pin it to the taskbar, put it on the desktop - it just runs.
echo.
pause
