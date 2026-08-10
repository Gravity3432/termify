@echo off
REM ============================================================
REM  Termify launcher for Windows
REM  made with heart by @johnthemailboy
REM  Keeps the window open on error so you can read what broke.
REM ============================================================
cd /d "%~dp0"

REM --- find a Python interpreter (py launcher first, then python) ---
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo.
  echo  [termify] Could not find Python.
  echo  Install Python 3.10+ from https://python.org then run this again.
  echo.
  pause
  exit /b 1
)

REM --- create the virtual environment on first run ---
if not exist .venv (
  echo.
  echo  [termify] First run - creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo.
    echo  [termify] Could not create the virtual environment.
    echo  Make sure %PY% is a real Python install ^(python.org^) and is 3.10+.
    echo.
    pause
    exit /b 1
  )
  .venv\Scripts\python -m pip install --quiet --upgrade pip
  if errorlevel 1 goto :pip_fail
  .venv\Scripts\python -m pip install --quiet -r requirements.txt
  if errorlevel 1 goto :pip_fail
)

REM --- run Termify ---
.venv\Scripts\python -m termify %*
if errorlevel 1 goto :run_fail
exit /b 0

:pip_fail
echo.
echo  [termify] Could not install the required packages.
echo  Check your internet connection, then run this again.
echo.
pause
exit /b 1

:run_fail
echo.
echo  [termify] Termify exited with an error.
echo  See the message above. If it says 'spotipy' or 'requests',
echo  the packages may not be installed - delete the .venv folder
echo  and run this file again.
echo.
pause
exit /b 1
