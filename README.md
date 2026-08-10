# 🎧 Termify

A slick **terminal-based Spotify client** that plays your music right from the
command line — so you can ditch the heavy desktop app. Full color-shifting ASCII
art UI, album art rendered in the terminal, live playback, and every control you'd
expect.

> made with ♥ by **@johnthemailboy**

---

## ✨ Features

- **Embedded playback** — Termify streams, decodes and plays tracks itself via
  librespot + PyAV. No Spotify desktop app needed. Controls are instant and local.
- **Full transport controls** — play/pause, next/previous, seek, volume,
  shuffle, repeat, queue jump.
- **Browse your library** — playlists (all songs, no cap), Liked Songs, search
  (tracks/albums/artists), recently played, queue.
- **Karaoke lyrics** — synced lines from LRCLib with a Genius fallback.
- **Stunning ASCII UI** — gradient "splash" banner, album art as truecolor
  half-block art, an animated visualizer, 6 themes you can cycle with `t`.
- **Mouse support** — click zones, double-click to play, wheel scroll,
  right-click to add a song to a playlist.
- **Sort your lists** — press `o` to cycle: default → **date added** → title →
  artist → album → duration.
- **Date added** — see exactly when each song was added to a playlist.
- **JTMB boot splash** — a "JOHN THE MAIL BOY" neon animation on launch.

---

## ⚠️ Requirements

- **Spotify Premium.** This is Spotify's rule for *any* third-party playback
  (playback endpoints / streaming are Premium-only). Termify is unofficial and
  for your own personal use.
- **Python 3.10+** installed on your machine.
- **macOS / Linux:** one audio package (`libportaudio2`) so sound can play:
  - Debian/Ubuntu: `sudo apt install libportaudio2`
  - macOS: `brew install portaudio` *(usually already present)*
- **Windows:** the `run.bat` handles everything automatically.

---

## 🚀 Quick start

### Windows
Double-click **`run.bat`**. On first run it creates a virtual environment,
installs the requirements, then launches Termify.

### macOS / Linux
```bash
./run.sh
```

### Or manually
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m termify --demo         # try the offline demo first — no login needed
python -m termify                # the real thing
```

---

## 🎬 First real run (one-time setup)

Termify walks you through this the first time:

1. It asks for a **Client ID**. Create a free Spotify Developer app at
   `https://developer.spotify.com/dashboard` and set its redirect URI to:
   ```
   http://127.0.0.1:4615/callback
   ```
   Paste the Client ID back into Termify.
2. Your browser opens once to authorize library access.
3. Your browser opens once more to authorize the embedded audio player.
4. That's it — music plays from the terminal.

If anything about the first song doesn't start, Termify says why in plain
English at the bottom of the screen.

---

## 🎮 Controls

| Key | Action |
|-----|--------|
| `space` | Play / pause |
| `n` / `b` | Next / previous |
| `←` / `→` | Seek -5s / +5s |
| `+` / `-` | Volume up / down |
| `s` | Shuffle |
| `r` | Repeat (off → context → track) |
| `l` | Like / unlike current song |
| `/` | Search |
| `o` | Sort current list (default → date added → title → artist → album → duration) |
| `1`–`7` | Jump to view (home, search, playlists, liked, library, devices, queue) |
| `u` | Queue |
| `t` | Cycle theme |
| `M` | Diagnostics (mouse + last key) |
| `?` | Help overlay |
| `q` | Quit |

**Mouse:** click rows to select, double-click to play, wheel to scroll,
drag the progress/volume bars, right-click a track to add it to a playlist.

---

## 🗂 Project layout

```
termify/
├── termify/          # the app package (.py files)
├── requirements.txt  # Python dependencies
├── run.bat           # Windows launcher (CRLF)
├── run.sh            # macOS/Linux launcher
└── termify.zip       # release zip of the app package
```

---

## 🛠 Troubleshooting

- **"a Premium account is required"** — playback is Premium-only (Spotify's rule).
- **Song won't start / "decoder" message** — Termify now auto-heals and re-downloads
  the song silently, and auto-skips if a track truly refuses.
- **Mouse clicks not working** — use **Windows Terminal** (not old `cmd`), and
  press `M` to check whether the terminal is sending mouse events.
- **No active device** — you don't need one in embedded mode. In remote mode,
  open Spotify on your phone or web player once.

---

## 📜 Disclaimer

Termify is an **unofficial**, personal-use client. It is not affiliated with or
endorsed by Spotify. It only streams to your own Premium account, per your own
usage. Use responsibly.
