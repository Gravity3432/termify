# Contributing to Termify

Thanks for wanting to help! 🎧 This is a friendly, small project — no need to
be a git expert. Here's how to jump in.

## Ways to contribute

- **Report a bug** — open an issue with what you did, what you expected, and
  what happened. If you can, paste the footer (press `M` in the app) and your
  terminal/OS.
- **Suggest a feature** — open an issue describing the idea and why it'd help.
- **Fix something / add a feature** — see below.

## Quick start for contributors

```bash
git clone https://github.com/Gravity3432/termify.git
cd termify
python3 install.py        # or install.bat on Windows
./run.sh                  # launch; press ] to flip layouts, t for themes
```

## Code layout

- `termify/ui.py` — all the rendering (layouts, themes, widgets)
- `termify/app.py` — the main loop, key handling, views, state
- `termify/stream_engine.py` — embedded audio playback (librespot + PyAV)
- `termify/catalog.py` — Spotify Web API calls
- `termify/stats.py`, `termify/lyrics.py`, `termify/media_keys.py` — extras

## Before submitting

1. Make sure the app still starts: `python3 -m termify --demo`
2. Run the test suites (if present):
   ```bash
   for t in tests/*.py; do python3 "$t" 2>&1 | tail -1; done
   ```
   (Suites currently live at the repo root as `test_*.py`.)
3. Keep changes focused; one feature/fix per PR.

## Notes

- Termify is an **unofficial**, personal-use client. It's not affiliated with
  or endorsed by Spotify. It only streams to your own Premium account.
- The code is MIT licensed — feel free to fork it for your own use.
