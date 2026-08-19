@echo off
REM ============================================================
REM  Termify launcher (Windows)
REM  First run: runs the auto-installer, then opens the app.
REM  made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Termify

REM --- first run: auto-install everything ---
if not exist .venv\Scripts\python.exe (
  if exist install.py (
    where py >nul 2>nul && py install.py
    if errorlevel 1 (
      where python >nul 2>nul && python install.py
    )
  )
)

REM --- make sure install finished ---
if not exist .venv\Scripts\python.exe (
  echo.
  echo  [termify] Setup hasn't finished.
  echo  Please run install.py (or install.bat) once, then run this again.
  echo.
  pause
  exit /b 1
)

REM --- launch ---
.venv\Scripts\python -m termify %*
if errorlevel 1 goto :run_fail
exit /b 0

:run_fail
echo.
echo  [termify] Termify exited with an error.
echo  If it mentions missing packages, run install.py to reinstall them.
echo.
pause
exit /b 1
