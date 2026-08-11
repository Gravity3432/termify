#!/bin/sh
# ============================================================
#  Termify launcher for macOS / Linux
#  made with heart by @johnthemailboy
#  First run uses the friendly installer, then launches.
# ============================================================
cd "$(dirname "$0")" || exit 1

# first run -> friendly installer (if present)
if [ ! -d .venv ]; then
  if [ -f install.py ]; then
    python3 install.py || python install.py || {
      echo
      echo "  [termify] Setup didn't finish. Run:  python3 install.py"
      exit 1
    }
  fi
fi

if [ ! -d .venv ]; then
  echo
  echo "  [termify] Setup hasn't finished yet. Run:  python3 install.py"
  exit 1
fi

exec ./.venv/bin/python -m termify "$@"
