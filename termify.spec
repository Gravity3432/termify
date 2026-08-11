# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Termify.

Build with:  build_exe.bat   (on Windows)

This produces a single 'Termify.exe'. Note that Termify needs to read its
own package files at runtime (album-art templates etc.), so we bundle them
as data. If audio output ever fails from the exe, you can still use run.bat /
install.bat which is the more reliable path.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
# bundle the termify package so the exe can import it and find its data
datas += collect_data_files("termify", include_py_files=True)

hiddenimports = []
# PyInstaller sometimes misses dynamically imported libs:
hiddenimports += collect_submodules("termify")
hiddenimports += ["sounddevice", "numpy", "PIL", "rich", "readchar", "requests"]


a = Analysis(
    ["termify/__main__.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Termify",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # console app (we need the terminal UI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
