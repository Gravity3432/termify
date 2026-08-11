@echo off
REM ============================================================
REM  Termify launcher for Windows
REM  made with heart by @johnthemailboy
REM  First run goes through the friendly installer, then launches.
REM ============================================================
cd /d "%~dp0"
title Termify

REM --- first run: use the installer for a safe, guided setup ---
if not exist .venv (
  if exist install.py (
    where py >nul 2>nul && py install.py
    if errorlevel 1 (
      where python >nul 2>nul && python install.py
    )
  )
)

REM --- make sure the venv exists (installer may have been skipped) ---
if not exist .venv\Scripts\python.exe (
  echo.
  echo  [termify] Setup hasn't finished yet.
  echo  Please double-click install.bat once to set things up.
  echo.
  pause
  exit /b 1
)

REM --- launch Termify ---
.venv\Scripts\python -m termify %*
if errorlevel 1 goto :run_fail
exit /b 0

:run_fail
echo.
echo  [termify] Termify exited with an error.
echo  See the message above. If it mentions missing packages,
echo  double-click install.bat to reinstall them.
echo.
pause
exit /b 1
