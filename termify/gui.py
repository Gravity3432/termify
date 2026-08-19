"""Termify GUI — a windowed Spotify player built on the same engine as the
terminal app. Uses tkinter (built-in, no extra deps) so it stays easy to
package into a .exe and runs on Windows/macOS/Linux.

The GUI talks to the *same* engine objects (stream/remote/demo) through their
clean public API, so it inherits all the tested playback logic.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from .models import Snapshot

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except Exception:  # pragma: no cover
    _HAS_PIL = False

# Spotify-ish palette
BG = "#121212"
PANEL = "#1a1a1a"
TEXT = "#e6e6e6"
MUTED = "#8a8a8a"
ACCENT = "#1db954"   # spotify green
ACCENT_DIM = "#168f40"


class TermifyGUI:
    """A simple, clean windowed player."""

    def __init__(self, engine, cfg: dict):
        self.engine = engine
        self.cfg = cfg
        self.volume = int(cfg.get("volume", 60))
        self._stop = threading.Event()
        self._last_art_url = None
        self._art_photo = None

        import tkinter as tk
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Termify")
        self.root.geometry("760x520")
        self.root.configure(bg=BG)
        self.root.minsize(560, 400)

        self._build_widgets()
        self._bind_keys()

        # engine callbacks + startup
        self.engine.start(self._toast)
        self.snap: Snapshot = self.engine.snapshot()

        # poller keeps the UI in sync
        self._poller = threading.Thread(target=self._poll_loop, daemon=True)
        self._poller.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------- ui
    def _build_widgets(self) -> None:
        import tkinter as tk

        # ---- left: playlist column ----
        self.left = tk.Frame(self.root, bg=PANEL, width=200)
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)
        tk.Label(self.left, text="PLAYLISTS", bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 6))
        self.playlist_box = tk.Listbox(self.left, bg=PANEL, fg=TEXT,
                                       selectbackground=ACCENT, selectforeground="#000",
                                       highlightthickness=0, bd=0,
                                       font=("Segoe UI", 10))
        self.playlist_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.playlist_box.bind("<Double-Button-1>", lambda e: self._play_playlist())
        # refresh button
        tk.Button(self.left, text="↻ refresh", bg=PANEL, fg=TEXT, bd=0,
                  activebackground=ACCENT, command=self._refresh_playlists,
                  font=("Segoe UI", 9)).pack(fill="x", padx=8, pady=(0, 10))

        # ---- right: main column ----
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="right", fill="both", expand=True)

        # art + now playing
        top = tk.Frame(self.main, bg=BG)
        top.pack(fill="x", padx=20, pady=(20, 8))
        self.art_label = tk.Label(top, bg=BG, text="♪", fg=ACCENT,
                                  font=("Segoe UI", 40), width=6, height=3)
        self.art_label.pack(side="left")
        info = tk.Frame(top, bg=BG)
        info.pack(side="left", padx=16, fill="x", expand=True)
        self.title_lbl = tk.Label(info, text="Nothing playing", bg=BG, fg=TEXT,
                                  font=("Segoe UI", 18, "bold"), anchor="w")
        self.title_lbl.pack(anchor="w")
        self.artist_lbl = tk.Label(info, text="—", bg=BG, fg=MUTED,
                                   font=("Segoe UI", 12), anchor="w")
        self.artist_lbl.pack(anchor="w")
        self.album_lbl = tk.Label(info, text="", bg=BG, fg=MUTED,
                                  font=("Segoe UI", 10), anchor="w")
        self.album_lbl.pack(anchor="w")

        # progress
        prog = tk.Frame(self.main, bg=BG)
        prog.pack(fill="x", padx=20)
        self.progress = tk.Canvas(prog, height=6, bg=PANEL,
                                  highlightthickness=0, bd=0)
        self.progress.pack(fill="x")
        self.time_lbl = tk.Label(self.main, text="0:00 / 0:00", bg=BG, fg=MUTED,
                                 font=("Segoe UI", 9))
        self.time_lbl.pack(anchor="w", padx=20)
        self.progress.bind("<Button-1>", self._click_seek)
        self.progress.bind("<B1-Motion>", self._click_seek)

        # controls
        ctl = tk.Frame(self.main, bg=BG)
        ctl.pack(fill="x", padx=20, pady=(10, 6))
        self.btn_prev = tk.Button(ctl, text="⏮", bg=BG, fg=TEXT, bd=0, width=4,
                                  font=("Segoe UI", 14), activebackground=BG,
                                  command=self._prev)
        self.btn_prev.pack(side="left", padx=4)
        self.btn_play = tk.Button(ctl, text="▶", bg=ACCENT, fg="#000", bd=0,
                                  width=6, font=("Segoe UI", 14, "bold"),
                                  activebackground=ACCENT_DIM, command=self._toggle)
        self.btn_play.pack(side="left", padx=4)
        self.btn_next = tk.Button(ctl, text="⏭", bg=BG, fg=TEXT, bd=0, width=4,
                                  font=("Segoe UI", 14), activebackground=BG,
                                  command=self._next)
        self.btn_next.pack(side="left", padx=4)
        self.lbl_state = tk.Label(ctl, text="● idle", bg=BG, fg=MUTED,
                                  font=("Segoe UI", 9))
        self.lbl_state.pack(side="left", padx=12)

        # volume + shuffle/repeat
        bot = tk.Frame(self.main, bg=BG)
        bot.pack(fill="x", padx=20, pady=(4, 8))
        tk.Label(bot, text="🔊", bg=BG, fg=MUTED).pack(side="left")
        self.vol = tk.Scale(bot, from_=0, to=100, orient="horizontal", bg=BG,
                            fg=TEXT, highlightthickness=0, bd=0,
                            troughcolor=PANEL, activebackground=ACCENT,
                            command=self._set_volume)
        self.vol.set(self.volume)
        self.vol.pack(side="left", fill="x", expand=True, padx=8)
        self.btn_shuffle = tk.Button(bot, text="⇄", bg=BG, fg=MUTED, bd=0, width=3,
                                     font=("Segoe UI", 12), command=self._shuffle)
        self.btn_shuffle.pack(side="right", padx=2)
        self.btn_repeat = tk.Button(bot, text="↻", bg=BG, fg=MUTED, bd=0, width=3,
                                    font=("Segoe UI", 12), command=self._repeat)
        self.btn_repeat.pack(side="right", padx=2)

        # queue
        tk.Label(self.main, text="UP NEXT", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)
        self.queue_box = tk.Listbox(self.main, bg=BG, fg=TEXT,
                                    highlightthickness=0, bd=0,
                                    font=("Segoe UI", 10))
        self.queue_box.pack(fill="both", expand=True, padx=20, pady=(2, 12))

        self._toast_lbl = tk.Label(self.main, text="", bg=BG, fg=ACCENT,
                                   font=("Segoe UI", 9))
        self._toast_lbl.pack(side="bottom", pady=4)

    def _bind_keys(self) -> None:
        self.root.bind("<space>", lambda e: self._toggle())
        self.root.bind("<Left>", lambda e: self._seek(-5))
        self.root.bind("<Right>", lambda e: self._seek(5))

    # ------------------------------------------------------- engine wiring
    def _toast(self, msg: str) -> None:
        try:
            self.root.after(0, lambda: self._toast_lbl.config(text=str(msg)))
        except Exception:
            pass

    def _refresh_playlists(self) -> None:
        def work():
            try:
                pls = self.engine.get_playlists()
            except Exception:
                pls = []
            names = [p.name for p in pls]
            self.root.after(0, lambda: self._fill_playlists(names, pls))
        threading.Thread(target=work, daemon=True).start()

    def _fill_playlists(self, names, pls):
        self._playlists = pls
        self.playlist_box.delete(0, "end")
        for n in names:
            self.playlist_box.insert("end", n)

    def _play_playlist(self):
        sel = self.playlist_box.curselection()
        if sel and hasattr(self, "_playlists") and sel[0] < len(self._playlists):
            pl = self._playlists[sel[0]]
            self._toast(f"playing {pl.name}…")
            threading.Thread(target=self.engine.play_playlist, args=(pl,),
                             daemon=True).start()

    # ------------------------------------------------------------ transport
    def _toggle(self):
        if self.snap.playing:
            threading.Thread(target=self.engine.toggle, daemon=True).start()
        else:
            threading.Thread(target=self.engine.toggle, daemon=True).start()

    def _next(self):
        threading.Thread(target=self.engine.next, daemon=True).start()

    def _prev(self):
        threading.Thread(target=self.engine.prev, daemon=True).start()

    def _seek(self, delta_sec):
        self._seek_ms(int(self.snap.position_ms) + delta_sec * 1000)

    def _seek_ms(self, ms):
        threading.Thread(target=self.engine.seek_ms, args=(int(ms),),
                         daemon=True).start()

    def _click_seek(self, event):
        try:
            w = max(1, event.widget.winfo_width())
            ratio = max(0.0, min(1.0, event.x / w))
            self._seek_ms(int(self.snap.duration_ms * ratio))
        except Exception:
            pass

    def _set_volume(self, v):
        self.volume = int(v)
        threading.Thread(target=self.engine.set_volume, args=(int(v),),
                         daemon=True).start()

    def _shuffle(self):
        threading.Thread(target=self.engine.shuffle_toggle, daemon=True).start()

    def _repeat(self):
        threading.Thread(target=self.engine.repeat_cycle, daemon=True).start()

    # -------------------------------------------------------------- refresh
    def _poll_loop(self):
        while not self._stop.is_set():
            try:
                self.snap = self.engine.snapshot()
                self._update_ui()
            except Exception:
                pass
            self._stop.wait(0.5)

    def _update_ui(self):
        snap = self.snap
        try:
            if snap.track:
                t = snap.track
                self.title_lbl.config(text=t.name)
                self.artist_lbl.config(text=t.artists)
                self.album_lbl.config(text=t.album)
                pos = int(snap.position_ms or 0)
                dur = int(snap.duration_ms or 0)
                self.time_lbl.config(text=f"{_fmt(pos)} / {_fmt(dur)}")
                self.progress.delete("all")
                w = max(1, self.progress.winfo_width())
                pct = (pos / dur) if dur else 0
                self.progress.create_rectangle(0, 0, int(w * pct), 6,
                                               fill=ACCENT, outline="")
                self.btn_play.config(text="❚❚" if snap.playing else "▶")
                self.lbl_state.config(text="● playing" if snap.playing
                                      else "❚❚ paused",
                                      fg=ACCENT if snap.playing else MUTED)
                if t.image_url != self._last_art_url:
                    self._last_art_url = t.image_url
                    self._load_art(t.image_url)
            else:
                self.title_lbl.config(text="Nothing playing")
                self.artist_lbl.config(text="—")
                self.btn_play.config(text="▶")
                self.lbl_state.config(text="● idle", fg=MUTED)
            # shuffle/repeat colors
            self.btn_shuffle.config(fg=ACCENT if snap.shuffle else MUTED)
            self.btn_repeat.config(fg=ACCENT if snap.repeat != "off" else MUTED)
            # queue
            q = snap.queue
            if len(q) != self.queue_box.size():
                self.queue_box.delete(0, "end")
                for i, tr in enumerate(q[:12]):
                    self.queue_box.insert("end", f"{i + 1}. {tr.name} — {tr.artists}")
        except Exception:
            pass

    def _load_art(self, url):
        if not _HAS_PIL or not url:
            return
        def work():
            try:
                import io
                import requests
                r = requests.get(url, timeout=8)
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                img = img.resize((96, 96))
                photo = ImageTk.PhotoImage(img)
                self._art_photo = photo  # keep ref
                self.root.after(0, lambda: self.art_label.config(
                    image=photo, text=""))
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    # --------------------------------------------------------------- run
    def run(self) -> None:
        self._refresh_playlists()
        self.root.mainloop()

    def _on_close(self):
        self._stop.set()
        try:
            self.engine.shutdown()
        except Exception:
            pass
        self.root.destroy()

    def quit(self) -> None:
        self._on_close()


def _fmt(ms: int) -> str:
    total = max(0, int(ms) // 1000)
    return f"{total // 60}:{total % 60:02d}"


def run_gui(engine, cfg: dict) -> None:
    gui = TermifyGUI(engine, cfg)
    gui.run()
