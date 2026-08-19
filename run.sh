#!/bin/sh
# ============================================================
#  Termify launcher (macOS / Linux)
#  First run: runs the auto-installer, then opens the app.
#  made with heart by @johnthemailboy
# ============================================================
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  python3 install.py || python install.py || {
    echo
    echo "  [termify] Setup didn't finish. Run:  python3 install.py"
    exit 1
  }
fi

if [ ! -d .venv ]; then
  echo
  echo "  [termify] Setup hasn't finished. Run:  python3 install.py"
  exit 1
fi

exec ./.venv/bin/python -m termify "$@"
