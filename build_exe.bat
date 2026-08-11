@echo off
REM ============================================================
REM  Build a Windows .exe for Termify using PyInstaller.
REM  Run this ONCE on your Windows machine (after install.bat).
REM  made with heart by @johnthemailboy
REM ============================================================
cd /d "%~dp0"
title Build Termify exe

REM --- use the project venv if it exists ---
set "PY=python"
if exist .venv\Scripts\python.exe set "PY=.venv\Scripts\python.exe"

echo.
echo  [termify] Installing PyInstaller...
%PY% -m pip install --quiet pyinstaller
if errorlevel 1 (
  echo  Could not install PyInstaller. Check your internet.
  pause
  exit /b 1
)

echo.
echo  [termify] Building Termify.exe (this can take a few minutes)...
%PY% -m PyInstaller --noconfirm --clean termify.spec
if errorlevel 1 (
  echo  Build failed. See the output above.
  pause
  exit /b 1
)

echo.
echo  [termify] Done! Your app is here:
echo    dist\Termify.exe
echo  You can pin it to the taskbar (right-click -^> Pin to taskbar),
echo  or right-click -^> Send to -^> Desktop for a shortcut.
echo.
pause
