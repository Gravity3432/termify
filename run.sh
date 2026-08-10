#!/bin/sh
# ============================================================
#  Termify launcher for macOS / Linux
#  made with heart by @johnthemailboy
# ============================================================
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo
  echo "  [termify] First run - creating virtual environment..."
  python3 -m venv .venv || {
    echo
    echo "  [termify] Could not create the virtual environment."
    echo "  Make sure python3 is 3.10+ (you may need python3-venv)."
    exit 1
  }
  ./.venv/bin/pip install --quiet --upgrade pip || exit 1
  ./.venv/bin/pip install --quiet -r requirements.txt || exit 1
fi

exec ./.venv/bin/python -m termify "$@"
