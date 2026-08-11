@echo off
REM ============================================================
REM  Termify installer (Windows)
REM  Double-click this to set up Termify safely & easily.
REM  made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Termify installer

REM find python (py launcher first, then python)
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)

if defined PY (
  %PY% install.py
) else (
  echo.
  echo  [termify] Could not find Python.
  echo  Please install Python 3.10+ from https://python.org
  echo  (tick "Add python.exe to PATH"), then run this again.
  echo.
  pause
)
