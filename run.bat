@echo off
REM ============================================================
REM  Termify launcher (Windows)
REM  First run: auto-installs, then walks you through the one-time
REM  Spotify login. Always keeps the window open so it never just
REM  vanishes. made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Termify

REM --- 1. auto-install everything on first run ---
if not exist .venv\Scripts\python.exe (
  if exist install.py (
    echo  First run - setting Termify up for you...
    where py >nul 2>nul && py install.py
    if errorlevel 1 (
      where python >nul 2>nul && python install.py
    )
  )
)

if not exist .venv\Scripts\python.exe (
  echo.
  echo  [termify] Setup hasn't finished. Run install.py once, then this again.
  pause
  exit /b 1
)

REM --- 2. one-time Spotify login (only if not set up yet) ---
set "NEEDSETUP="
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python -c "import json,os,pathlib,sys; cfg=json.loads((pathlib.Path(os.path.expanduser('~'))/'.termify'/'config.json').read_text()) if (pathlib.Path(os.path.expanduser('~'))/'.termify'/'config.json').exists() else {}; sys.exit(0 if cfg.get('client_id') else 1)" >nul 2>nul
  if errorlevel 1 set "NEEDSETUP=1"
)
if defined NEEDSETUP (
  echo.
  echo  Let's connect you to Spotify - it takes a minute.
  .venv\Scripts\python -m termify --setup
)

REM --- 3. launch ---
.venv\Scripts\python -m termify %*
set "EXITCODE=%errorlevel%"

echo.
echo  [termify] Termify closed (exit code %EXITCODE%).
echo  You can close this window.
echo.
pause
exit /b %EXITCODE%
