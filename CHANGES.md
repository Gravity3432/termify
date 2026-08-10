# Termify update — v0.2.0: stats, queue control, duplicate finder

made with ♥ by @johnthemailboy

## New in v0.2.0

- **📊 Listening stats** — press `S`. Tracks your listening locally in
  `~/.termify/stats.json`: minutes today / last 7 days / all time, a day
  streak, your top tracks & artists, and a **"your week in music"** report.
  Recorded automatically while you listen. Nothing is sent anywhere.
- **➡️ Play next / play later** — `N` queues the selected track to play right
  after the current one; `E` parks it at the end of the queue.
- **🧹 Duplicate finder** — press `F` inside a playlist (or Liked Songs) to fold
  the list down to just the duplicate songs; press `F` again to restore.

---

# Termify update — playlist fix + date added

made with ♥ by @johnthemailboy

## What was wrong
- Playlists were hard-capped at **500 songs**, so a 566-song playlist silently
  dropped the last 66 songs. Liked Songs had the same 500 cap.

## What changed

### 1. Full playlists & liked songs ✅
- `catalog.py` — `playlist_tracks()` and `liked()` now keep paging until Spotify
  reports every track has been fetched (`total`), instead of stopping at 500.
  (A 10,000 safety ceiling still protects against an endless loop.)
- Your 566-song playlist will now load all 566.

### 2. Date added ✅
- `models.py` — `Track` now carries `added_at` (the date Spotify says each song
  was added) plus a `date_text` helper.
- `catalog.py` — captures `added_at` from every playlist / liked entry.
- `app.py` — the **`o` sort key** now cycles through:
  `default → date added → title → artist → album → duration`.
- `ui.py` — while sorted by **date added**, the album column is replaced by the
  date (e.g. `2021-05-04`) so you can actually see it.
- `demo_engine.py` — demo tracks got fake dates so you can try it offline.
- `remote_engine.py` — raised the remote-mode play cap from 400 → 700 uris so
  big playlists also play through the phone/web-player path.

## Verified
- `test_fix.py` passes: 566-song playlist loads fully, 750-song liked list loads
  fully, `added_at` is captured, date sort is registered, empty lists stay safe.
- All 15 `.py` files compile cleanly.

## How to install
1. Download **`termify_updated.zip`**.
2. Extract it — you'll get a `termify` folder with the `.py` files.
3. On your PC, delete the old inner `termify` folder (the one with `app.py`).
4. Copy the new `termify` folder in its place.
5. Run `run.bat`. Keep `.venv`, `run.bat`, and `%USERPROFILE%\.termify` untouched.

Tip: in the app press `python -m termify --demo` first to see the date column,
or just open your big playlist — all 566 songs should be there now.
