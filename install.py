#!/usr/bin/env python3
"""Termify installer — does EVERYTHING for you, nothing manual.

What it handles automatically:
  1. Finds Python (or, on Windows, can download a portable one for you).
  2. Creates a private environment inside this folder (nothing touches
     your system; delete this folder to uninstall).
  3. Installs every package the app needs, with automatic retries and
     prebuilt binary wheels — so a flaky download can't kill the install.
  4. Tells you exactly how to launch when done.

It only uses the Python standard library, so it can run anywhere.
"""
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

APP = "Termify"
CORE_DEPS = ["spotipy", "librespot", "rich", "readchar", "requests"]
# binary/heavier ones installed with --prefer-binary so nothing compiles
BINARY_DEPS = ["numpy", "Pillow", "av", "sounddevice"]
OPTIONAL_DEPS = ["keyboard"]  # global media buttons; skip if it fails
OPTIONAL_DEPS += ["python-sixel-windows"]  # in-terminal real cover images; skippable (falls back to OS viewer)


# ---------------------------------------------------------------- helpers
def _spinner(msg):
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    while True:
        sys.stdout.write("\r  " + msg + " " + chars[i % len(chars)] + "   ")
        sys.stdout.flush()
        i += 1
        yield


def run(cmd, label, cwd=None):
    """Run a command with a spinner; returns (ok, output)."""
    anim = _spinner(f"{label}...")
    try:
        next(anim)
    except StopIteration:
        pass
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=600)
        ok = p.returncode == 0
        out = (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        ok, out = False, str(e)
    try:
        anim.close()
    except Exception:
        pass
    sys.stdout.write("\r" + " " * 70 + "\r")
    print(f"  {'\u2713' if ok else '\u2717'} {label}")
    return ok, out


def find_python():
    cands = []
    if sys.platform == "win32":
        for name in (["py", "python", "python3"]):
            try:
                r = subprocess.run([name, "-V"], capture_output=True, text=True)
                if r.returncode == 0:
                    cands.append(name)
            except Exception:
                pass
        return cands[0] if cands else None
    for name in ("python3", "python"):
        if shutil.which(name):
            return name
    return None


def version_ok(py):
    try:
        r = subprocess.run([py, "-V"], capture_output=True, text=True)
        m = re.search(r"(\d+)\.(\d+)", (r.stdout or r.stderr).strip())
        if m:
            major, minor = int(m.group(1)), int(m.group(2))
            return major > 3 or (major == 3 and minor >= 10)
    except Exception:
        pass
    return False


def download_portable_python(where):
    """Windows: fetch a portable CPython (has pip + venv) if none is installed."""
    print("  No Python found — downloading a portable one for you (~30 MB)...")
    ver = "3.12.4"
    tag = "20240615"
    base = "https://github.com/astral-sh/python-build-standalone/releases/download"
    url = (f"{base}/{tag}/cpython-{ver}+{tag}-x86_64-pc-windows-msvc-"
           f"install_only.tar.gz")
    dest = os.path.join(where, "_python")
    os.makedirs(dest, exist_ok=True)
    tarball = os.path.join(where, "_python.tar.gz")
    try:
        urllib.request.urlretrieve(url, tarball)
        import tarfile
        with tarfile.open(tarball, "r:gz") as tf:
            tf.extractall(dest)
        os.remove(tarball)
        # find python.exe inside
        for root, _dirs, files in os.walk(dest):
            if "python.exe" in files:
                return os.path.join(root, "python.exe")
    except Exception as e:
        print(f"  Could not download portable Python: {e}")
    return None


# ---------------------------------------------------------------- install
def pip_install(py_venv, packages, label):
    """Install a set of packages with retries + prefer-binary."""
    attempts = 3
    for i in range(attempts):
        print(f"  [{i + 1}/{attempts}] {label}...")
        cmd = [py_venv, "-m", "pip", "install", "--prefer-binary",
               "--disable-pip-version-check", "-q"] + packages
        ok, _out = run(cmd, f"installing {label}")
        if ok:
            return True
        if i < attempts - 1:
            print("    (a download hiccuped — retrying automatically)")
            time.sleep(2)
    return False


def main():
    print()
    print("  " + "=" * 44)
    print(f"   \u266a  {APP}  —  automatic setup")
    print("  " + "=" * 44)
    print("  I'll handle everything: Python, environment, and all")
    print("  the libraries Termify needs. Nothing else to install by hand.")
    print("  Everything stays in this folder — delete it to uninstall.")
    print()

    base = os.path.dirname(os.path.abspath(__file__))
    py = find_python()

    # --- 1. Python ---
    print("  [1/4] Making sure Python is available...")
    if py and version_ok(py):
        print(f"  \u2713 Using your Python: {py}")
    else:
        if sys.platform == "win32":
            py = download_portable_python(base)
        if not py:
            print("  \u2717 No working Python 3.10+ found.")
            print("  Install Python 3.10+ from https://python.org, then run this again.")
            input("\n  Press Enter to close...")
            return 1
        if not version_ok(py):
            print(f"  \u2717 {py} is not Python 3.10+.")
            input("\n  Press Enter to close...")
            return 1

    # --- 2. environment ---
    print("  [2/4] Creating a private environment (a minute)...")
    venv_dir = os.path.join(base, ".venv")
    venv_py = (os.path.join(venv_dir, "Scripts", "python.exe")
               if sys.platform == "win32"
               else os.path.join(venv_dir, "bin", "python"))
    if not os.path.exists(venv_py):
        ok, _ = run([py, "-m", "venv", ".venv"], "creating environment")
        if not ok:
            print("  \u2717 Could not create the environment.")
            input("\n  Press Enter to close...")
            return 1
    else:
        print("  \u2713 Environment already exists — reusing it")

    # --- 3. packages ---
    print("  [3/4] Installing libraries (downloads, with auto-retry)...")
    print("        This can take a few minutes on a slow connection.")
    ok, _ = run([venv_py, "-m", "pip", "install", "--upgrade", "pip",
                 "--disable-pip-version-check", "-q"], "upgrading pip")
    if not pip_install(venv_py, CORE_DEPS, "core libraries"):
        print("  \u2717 Core libraries failed after retries. Check internet, retry.")
        input("\n  Press Enter to close...")
        return 1
    if not pip_install(venv_py, BINARY_DEPS, "audio/image libraries"):
        print("  \u2717 Audio libraries failed after retries.")
        print("  If it mentions 'av' or 'sounddevice', your Python build may be")
        print("  the issue — installing Python 3.12 from python.org usually fixes it.")
        input("\n  Press Enter to close...")
        return 1
    pip_install(venv_py, OPTIONAL_DEPS, "optional media keys (skippable)")

    # --- 4. done ---
    print("  [4/4] Done!")
    print("  \u2713 Termify is installed and ready.")
    print()
    if sys.platform == "win32":
        print("  To open it:  double-click  run.bat")
    else:
        print("  To open it:  ./run.sh")
    print("  First launch asks you to log in to Spotify (Premium required).")
    print()
    input("  Press Enter to close...")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Setup cancelled. Run it again any time — it's safe.")
        sys.exit(1)
