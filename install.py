#!/usr/bin/env python3
"""Termify installer — a friendly, safe first-run setup.

What it does:
  1. Tells you exactly what's about to happen (and that nothing scary is).
  2. Finds a Python 3.10+ interpreter.
  3. Creates a local virtual environment inside THIS folder only.
  4. Installs the required packages, with live progress.
  5. Tells you it's done and how to launch.

Safety notes shown to the user:
  * Everything stays in this folder (.venv) — nothing touches your system.
  * No admin rights needed.
  * You can delete this folder any time to uninstall.
  * Your Spotify login is only stored on your machine in ~/.termify.

This script only uses the standard library, so it runs anywhere with Python.
"""
import os
import shutil
import subprocess
import sys
import time

APP = "Termify"
STEP_TOTAL = 4


# ---------------------------------------------------------------- helpers
def _clear_line():
    print("\r" + " " * 60 + "\r", end="", flush=True)


def spinner(msg):
    """Run a quick animated spinner for a blocking call."""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while True:
        _clear_line()
        print(f"  {msg} {chars[i % len(chars)]}", end="", flush=True)
        i += 1
        yield


def step(n, title):
    print(f"\n  [{n}/{STEP_TOTAL}] {title}")
    print("  " + "-" * 40)


def run(cmd, label, cwd=None):
    """Run a command with a spinner; returns True on success."""
    print()
    anim = spinner(f"{label}...")
    next(anim)
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        ok = proc.returncode == 0
    except Exception:
        ok = False
    try:
        anim.close()
    except Exception:
        pass
    _clear_line()
    if ok:
        print(f"  \u2713 {label} done")
    else:
        print(f"  \u2717 {label} failed")
    return ok


def find_python():
    """Return an interpreter string, or None."""
    candidates = []
    if sys.platform == "win32":
        # try the py launcher, then python
        for name in ("py -3", "python", "python3"):
            try:
                r = subprocess.run(name.split(), capture_output=True, text=True)
                if r.returncode == 0:
                    candidates.append(name.split()[0])
            except Exception:
                pass
        # prefer py
        for c in candidates:
            if c == "py":
                return c
        return candidates[0] if candidates else None
    else:
        for name in ("python3", "python"):
            if shutil.which(name):
                return name
    return None


def check_version(py):
    try:
        r = subprocess.run(f"{py} --version".split(), capture_output=True, text=True)
        out = (r.stdout or r.stderr).strip()
        # "Python 3.12.4" -> 3, 12
        import re
        m = re.search(r"(\d+)\.(\d+)", out)
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            if major > 3 or (major == 3 and minor >= 10):
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- main
def main():
    print()
    print("  " + "=" * 42)
    print(f"   \u266a  {APP}  —  first-time setup")
    print("  " + "=" * 42)
    print()
    print("  Hi! This one-time setup is quick and safe:")
    print("   \u2022 Everything installs into THIS folder only (.venv)")
    print("   \u2022 No admin rights needed, nothing added to your system")
    print("   \u2022 Your Spotify login stays on YOUR machine (~/.termify)")
    print("   \u2022 To uninstall later, just delete this folder")
    print()
    print("  Getting things ready...", flush=True)

    # 1 - find python
    step(1, "Checking for Python")
    py = find_python()
    if not py:
        print("  \u2717 No Python found.")
        print("  Please install Python 3.10+ from https://python.org")
        print("  (on Windows, tick \"Add python.exe to PATH\"), then run this again.")
        input("\n  Press Enter to close...")
        return 1
    if not check_version(py):
        print(f"  \u2717 Found '{py}' but it's not Python 3.10+.")
        print("  Please install Python 3.10+ from https://python.org")
        input("\n  Press Enter to close...")
        return 1
    print(f"  \u2713 Using {py}")

    base = os.path.dirname(os.path.abspath(__file__))
    venv_py = os.path.join(base, ".venv", "Scripts", "python.exe") if sys.platform == "win32" \
        else os.path.join(base, ".venv", "bin", "python")

    # 2 - create venv
    step(2, "Creating a private environment (a minute or two)")
    if not os.path.exists(venv_py):
        if not run([py, "-m", "venv", ".venv"], "Creating environment"):
            print("  \u2717 Could not create the virtual environment.")
            input("\n  Press Enter to close...")
            return 1
    else:
        print("  \u2713 Environment already exists — reusing it")

    # 3 - install packages
    step(3, "Installing the app's packages")
    print("  This is the big step — it downloads the libraries Termify")
    print("  needs. It can take a few minutes on a slow connection.")
    # upgrade pip
    run([venv_py, "-m", "pip", "install", "--upgrade", "pip"],
        "Upgrading pip")
    # install requirements with a progress indicator
    reqs = os.path.join(base, "requirements.txt")
    if not run([venv_py, "-m", "pip", "install", "-r", reqs], "Installing packages"):
        print()
        print("  \u2717 Some packages failed to install.")
        print("  Check your internet connection, then run this again.")
        print("  (A broken install is safe — just rerun and it retries.)")
        input("\n  Press Enter to close...")
        return 1

    # 4 - done
    step(4, "All done!")
    print("  \u2713 Termify is installed and ready.")
    print()
    if sys.platform == "win32":
        print("  To open it: double-click  run.bat   (or type: run.bat)")
    else:
        print("  To open it:  ./run.sh")
    print()
    print("  First launch asks you to log in to your Spotify account.")
    print("  (Requires Spotify Premium for playback.)")
    print()
    input("  Press Enter to close...")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Setup cancelled. Run it again any time — it's safe.")
        sys.exit(1)
