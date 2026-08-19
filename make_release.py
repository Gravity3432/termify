#!/usr/bin/env python3
"""Build a clean, tidy release zip.

Users shouldn't stare at a pile of files. This lays out the release so the
"do this" files are obvious and everything else is tucked into a dev/ folder.
"""
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "termify-release.zip")

# files a normal user actually interacts with, shown at the top level
USER_FILES = [
    "README.md",
    "run.bat",      # Windows: just double-click
    "run.sh",       # mac/linux
    "install.py",   # the automatic installer
    "build.bat",    # optional: make a standalone .exe
    "LICENSE",
]
# things only developers/builders need -> hidden in dev/
DEV_FILES = [
    "termify.spec", "entry.py", "pyproject.toml",
    "requirements.txt", "CONTRIBUTING.md",
    "test_errors.py", "test_features2.py", "test_fix.py",
    "test_media2.py", "test_media_lyrics.py", "make_release.py",
]


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    tmp = os.path.join(HERE, "_rel_tmp")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)

    # the app package
    shutil.copytree(os.path.join(HERE, "termify"),
                    os.path.join(tmp, "termify"))
    # docs (used by README)
    shutil.copytree(os.path.join(HERE, "docs"),
                    os.path.join(tmp, "docs"))

    # visible files
    for f in USER_FILES:
        if os.path.exists(os.path.join(HERE, f)):
            shutil.copy2(os.path.join(HERE, f), os.path.join(tmp, f))

    # dev-only files into a subfolder
    dev = os.path.join(tmp, "dev")
    os.makedirs(dev)
    for f in DEV_FILES:
        if os.path.exists(os.path.join(HERE, f)):
            shutil.copy2(os.path.join(HERE, f), os.path.join(dev, f))

    # add a "start here" pointer
    with open(os.path.join(tmp, "README.txt"), "w", encoding="utf-8") as f:
        f.write(
            "Welcome to Termify!\n"
            "===================\n\n"
            "TO INSTALL:  double-click  run.bat   (Windows)\n"
            "             or run  python3 install.py   then  ./run.sh  (Mac/Linux)\n\n"
            "It installs everything automatically - nothing to set up by hand.\n"
            "The full guide is in README.md. The dev/ folder is for builders only.\n"
        )

    # zip it, with top-level files first (nicer to browse)
    zf = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
    order = (["termify/"] + USER_FILES + ["README.txt", "docs/", "dev/"])
    # simple approach: write termify, README, README.txt, docs, dev
    for root, _dirs, files in os.walk(tmp):
        for fn in sorted(files):
            full = os.path.join(root, fn)
            arc = os.path.relpath(full, tmp)
            zf.write(full, arc)
    zf.close()
    shutil.rmtree(tmp)
    print("created", OUT)


if __name__ == "__main__":
    main()
