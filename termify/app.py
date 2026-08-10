from __future__ import annotations

import queue
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.live import Live

from . import art, config, ui
from .input_layer import (
    K_CTRL_C,
    K_DOWN,
    K_ENTER,
    K_ESC,
    K_LEFT,
    K_MEDIA_NEXT,
    K_MEDIA_PLAY,
    K_MEDIA_PREV,
    K_MEDIA_STOP,
    K_PGDN,
    K_PGUP,
    K_RIGHT,
    K_SPACE,
    K_UP,
    InputReader,
)
from .models import Snapshot, Track
from .catalog import Catalog
from .media_keys import MediaKeyController
from .stats import Stats, fmt_ms

FPS = 20

VIEW_ORDER = ["home", "search", "playlists", "liked", "library", "devices", "queue", "lyrics"]

# Spotify-style sort cycle for track lists (None = original order)
SORT_MODES = [
    ("default", None),
    ("date added", lambda t: t.added_at or ""),
    ("title", lambda t: (t.name or "").lower()),
    ("artist", lambda t: (t.artists or "").lower()),
    ("album", lambda t: (t.album or "").lower()),
    ("duration", lambda t: t.duration_ms),
]
SORTABLE = {"liked", "playlist_tracks", "album", "artist"}


class _Frame:
    def __init__(self, app):
        self.app = app

    def __rich_console__(self, console, options):
        size = console.size
        yield self.app.render(size.width, size.height)


class App:
    def __init__(self, engine, cfg: dict, demo: bool = False):
        self.engine = engine
        self.cfg = cfg
        self.demo = demo
        self.theme = cfg.get("theme", "aurora")
        self._t0 = time.monotonic()
        self.boot_until = self._t0 + 4.2  # JTMB splash; any key cuts it short

        self.view = "home"
        self.help_visible = False
        self.rows = {
            "search": [], "playlists": [], "liked": [],
            "playlist_tracks": [], "devices": [], "library": [],
        }
        self.sel = defaultdict(int)
        self.scroll = defaultdict(int)
        self.loading = defaultdict(bool)
        self.current_pl = None
        self.current_artist = None
        self.current_album = None
        self.search_q = ""
        self.typing = False
        self.type_buf = ""

        # mouse / sorting state
        self.zones: list = []
        self.rows_orig: dict = {}
        self.sort_idx = defaultdict(int)
        self._last_click = (None, None, 0.0)
        self._drag_zone = None
        self._drag_last = 0.0
        self.input = InputReader()
        self.mouse_debug = False
        self._last_mouse: tuple = (0, 0, 0, "")

        # lyrics / picker / sleep timer / session resume / stats
        self.show_stats = False
        self.show_lyrics = False
        self.lyrics_state = {"id": None, "synced": [], "plain": [], "loading": False}
        self._lyrics_track_id = None
        self.picker = None  # {"track": Track, "sel": int}
        self.typing_target = "search"  # or "playlist"
        self.sleep_end = None
        self._sleep_mins = None
        self._resume_offer = cfg.get("last_session") or None
        self.live_bands = None
        self._dupes_active = False
        self._dupes_orig = []

        # global keyboard media-button hook (optional, non-fatal)
        self.media_keys = MediaKeyController()
        self._media_enabled = bool(cfg.get("media_keys", True))

        # local listening stats
        self.stats = Stats(config.APP_DIR / "stats.json")
        self._stats_last_ms = 0          # last known position for elapsed calc
        self._stats_track = None         # track we're currently counting

        self.snap = Snapshot(
            volume=int(cfg.get("volume", 60)),
            device_label=getattr(engine, "device_label", ""),
        )
        self._toasts = deque()
        self._toast_lock = threading.Lock()
        self._art_cache = {}
        self._art_pending = set()
        self._art_lock = threading.Lock()
        self._stop = threading.Event()
        self._poll_now = threading.Event()
        self._pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="termify")
        self._loaded_views = set()

    # ------------------------------------------------------------ helpers
    def t(self) -> float:
        return time.monotonic() - self._t0

    def boot_active(self) -> bool:
        return time.monotonic() < self.boot_until

    def boot_t(self) -> float:
        return min(4.2, max(0.0, time.monotonic() - self._t0))

    def boot_skip(self) -> None:
        self.boot_until = 0.0

    def toast(self, msg: str, secs: float = 4.0) -> None:
        with self._toast_lock:
            self._toasts.append((str(msg), time.monotonic() + secs))
            while len(self._toasts) > 6:
                self._toasts.popleft()

    def current_toast(self) -> str:
        now = time.monotonic()
        with self._toast_lock:
            while self._toasts and self._toasts[0][1] < now:
                self._toasts.popleft()
            return self._toasts[0][0] if self._toasts else ""

    def render(self, width: int, height: int):
        if self.boot_active():
            try:
                self.zones.clear()
                return ui.render_splash(self, width, height)
            except Exception:  # a splash bug must never delay the music
                self.boot_skip()
        try:
            get = getattr(self.engine, "get_bands", None)
            self.live_bands = get() if callable(get) else None
        except Exception:
            self.live_bands = None
        try:
            return ui.build(self, width, height)
        except Exception as exc:  # a render bug must NEVER freeze the UI
            from rich.panel import Panel
            from rich.text import Text

            return Panel(
                Text(
                    f"render hiccup (files updated halfway?): {exc}\n\n"
                    "tip: re-copy the whole termify\\termify folder from the repo",
                    style="grey70",
                ),
                title="termify",
            )

    # ------------------------------------------------------------ album art
    def art_for(self, url, w: int, h: int):
        if not url:
            return art.placeholder_art(w, h)
        key = (url, w, h)
        with self._art_lock:
            hit = self._art_cache.get(key)
        if hit is not None:
            return hit
        with self._art_lock:
            if key not in self._art_pending:
                self._art_pending.add(key)
                self._pool.submit(self._art_worker, url, w, h)
        return art.placeholder_art(w, h)

    def _art_worker(self, url: str, w: int, h: int) -> None:
        try:
            txt = art.cover_art_text(url, w, h) or art.placeholder_art(w, h)
        except Exception:
            txt = art.placeholder_art(w, h)
        with self._art_lock:
            self._art_cache[(url, w, h)] = txt
            self._art_pending.discard((url, w, h))

    # ------------------------------------------------------------ polling
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            interval = 2.2 if self.engine.mode == "remote" else 0.35
            try:
                if self.engine.mode == "remote":
                    self.engine.refresh()
                self.snap = self.engine.snapshot()
                self._tick_features()
            except Exception as exc:  # noqa: BLE001
                self.snap = Snapshot(
                    status="error", message=str(exc),
                    device_label=getattr(self.engine, "device_label", ""),
                )
            self._poll_now.wait(interval)
            self._poll_now.clear()

    def refresh_now(self) -> None:
        self._poll_now.set()

    # ------------------------------------------------ feature heartbeat
    def _tick_features(self) -> None:
        """Runs every snapshot: lyrics fetching on track change + sleep timer."""
        tr = self.snap.track
        tid = tr.id if tr else None
        if tid != self._lyrics_track_id:
            self._lyrics_track_id = tid
            self.lyrics_state = {"id": tid, "synced": [], "plain": [],
                                 "loading": bool(tr)}
            if tr:
                self._pool.submit(self._fetch_lyrics, tr)
        if self.sleep_end is not None and time.monotonic() >= self.sleep_end:
            self.sleep_end = None
            self._sleep_mins = None
            if self.snap.playing:
                self._call(self.engine.toggle)
            self.toast("😴 sleep timer hit zero - pausing. rest well ♪", 6)
        self._record_stats()

    def _fetch_lyrics(self, track) -> None:
        try:
            data = self.engine.lyrics_for(track) or {}
        except Exception:
            data = {}
        if self._lyrics_track_id != track.id:
            return  # listener already skipped ahead; drop stale result
        self.lyrics_state = {
            "id": track.id,
            "synced": data.get("synced") or [],
            "plain": data.get("plain") or [],
            "source": data.get("source") or "",
            "loading": False,
        }

    def _record_stats(self) -> None:
        """Accumulate the time actually spent listening into local stats."""
        tr = self.snap.track
        if tr is None:
            self._stats_track = None
            self._stats_last_ms = 0
            return
        pos = self.snap.position_ms
        if self._stats_track is not None and self._stats_track.uri == tr.uri:
            # same track continuing; credit the forward progress (skip seeks back)
            if self.snap.playing and pos > self._stats_last_ms:
                self.stats.add_play(tr, pos - self._stats_last_ms)
        self._stats_track = tr
        self._stats_last_ms = pos

    # ------------------------------------------------------------ data views
    def ensure_view(self, view: str, force: bool = False) -> None:
        if view in ("home", "search", "queue", "lyrics"):
            return  # snapshot-driven views need no fetching
        if view in self._loaded_views and not force:
            return
        self._loaded_views.add(view)
        if view == "playlists":
            self._load_list("playlists", self.engine.get_playlists)
        elif view == "liked":
            self._load_list("liked", self.engine.get_liked)
        elif view == "devices":
            if self.engine.mode == "remote":
                self._load_list("devices", self.engine.devices)
            else:
                self.rows["devices"] = []
        elif view == "library":
            self._load_list("library", self._fetch_library)
        elif view == "playlist_tracks":
            pass  # loaded by open_playlist

    def _fetch_library(self):
        """Stats & history: recently played, top tracks, top artists."""
        rows = []
        for label, fetch in (
            ("RECENTLY PLAYED", self.engine.recently_played),
            ("YOUR TOP TRACKS · last 4 weeks", self.engine.top_tracks),
        ):
            try:
                items = fetch() or []
            except Exception:
                items = []
            if items:
                rows.append(("section", label))
                rows += [("track", tr) for tr in items[:10]]
        try:
            artists = self.engine.top_artists() or []
        except Exception:
            artists = []
        if artists:
            rows.append(("section", "YOUR TOP ARTISTS"))
            rows += [("artist", a) for a in artists[:10]]
        if not rows:
            rows = [("section", "nothing here yet - go listen to something first ♪")]
        return rows

    def _load_list(self, kind: str, fetch) -> None:
        self.loading[kind] = True

        def work():
            try:
                data = fetch()
            except Exception as exc:  # noqa: BLE001
                self.toast(f"couldn't load {kind}: {exc}")
                data = []
            self.rows_orig[kind] = list(data)
            self._apply_sort(kind)
            self.loading[kind] = False
            self.clamp_sel(kind)

        self._pool.submit(work)

    def open_playlist(self, pl) -> None:
        self.current_pl = pl
        self.view = "playlist_tracks"
        self.sel["playlist_tracks"] = 0
        self.scroll["playlist_tracks"] = 0
        self._load_list("playlist_tracks", lambda: self.engine.get_playlist_tracks(pl))

    def open_liked(self) -> None:
        self.view = "liked"
        self.ensure_view("liked", force=True)

    # ------------------------------------------------------------ input
    def add_zone(self, x: int, y: int, w: int, h: int, **action) -> None:
        if w > 0 and h > 0:
            self.zones.append({"x": x, "y": y, "w": w, "h": h, **action})

    def find_zone(self, x: int, y: int):
        for z in reversed(self.zones):
            if z["x"] <= x < z["x"] + z["w"] and z["y"] <= y < z["y"] + z["h"]:
                return z
        return None

    def _input_loop(self) -> None:
        while not self._stop.is_set():
            try:
                ev = self.input.read_event()
            except Exception:
                time.sleep(0.05)
                continue
            if not ev:
                continue
            try:
                if ev[0] == "key":
                    self.dispatch(ev[1])
                elif ev[0] == "mouse":
                    self.on_mouse(ev[1], ev[2], ev[3], ev[4])
            except Exception as exc:  # noqa: BLE001
                self.toast(f"error: {exc}")

    # -- mouse ----------------------------------------------------------
    def on_mouse(self, code: int, x: int, y: int, pressed: bool) -> None:
        if self.boot_active():
            self.boot_skip()
            return
        z_seen = self.find_zone(x, y)
        self._last_mouse = (code, x, y, z_seen["type"] if z_seen else "miss")
        self._last_mouse_t = time.monotonic()
        motion = bool(code & 32)
        wheel = bool(code & 64)
        btn = code & 3
        if wheel:
            up = not (code & 1)  # 64 up / 65 down - smooth 1-row glides now
            z = self.find_zone(x, y)
            if z and z.get("type") == "volume":
                self._vol(3 if up else -3)
            elif self.picker is not None:
                rows = self.rows.get("playlists", [])
                self.picker["sel"] = max(0, min(max(0, len(rows) - 1),
                                                self.picker["sel"] + (-1 if up else 1)))
            else:
                self._move(-1 if up else 1)
            return
        if pressed and btn == 2:  # RIGHT click = add-that-song-to-a-playlist
            self._right_click(self.find_zone(x, y))
            return
        if motion and self._drag_zone is not None:
            if time.monotonic() - self._drag_last < 0.08:
                return
            self._drag_last = time.monotonic()
            z = self._drag_zone
            if z["type"] == "volume":
                self._set_volume_at(z, x)
            elif z["type"] == "seek":
                self._seek_at(z, x)
            return
        if pressed and btn == 0:
            z = self.find_zone(x, y)
            if z is None:
                return
            kind = z.get("type")
            if kind == "volume":
                self._set_volume_at(z, x)
                self._drag_zone = z
            elif kind == "seek":
                self._seek_at(z, x)
                self._drag_zone = z
            elif kind == "nav":
                self.goto(z["view"])
            elif kind == "btn":
                a = z.get("action")
                if a == "toggle":
                    self.snap.playing = not self.snap.playing
                    self._call(lambda: self.engine.toggle())
                elif a == "next":
                    self._call(self.engine.next)
                elif a == "prev":
                    self._call(self.engine.prev)
                elif a == "repeat":
                    self._call_toggled(self.engine.repeat_cycle, "repeat",
                                       {"off": "off", "context": "all", "track": "one"})
                elif a == "shuffle":
                    self._call_toggled(self.engine.shuffle_toggle, "shuffle")
            elif kind == "queue":
                i = z["index"]
                self.toast("jumping in queue…")
                qp = getattr(self.engine, "queue_play", None)
                if callable(qp):
                    self._call(lambda: qp(i))
            elif kind == "picker":
                if self.picker is not None:
                    now = time.monotonic()
                    same = self.picker["sel"] == z["index"]
                    self.picker["sel"] = z["index"]
                    if same and now - getattr(self, "_picker_click_t", 0.0) < 0.45:
                        self._picker_add()  # double-click adds
                    self._picker_click_t = now
            elif kind == "select":
                self._click_select(z)
            return
        if not pressed:
            self._drag_zone = None

    def _right_click(self, z) -> None:
        """Right-click a track row → straight into the add-to-playlist picker."""
        if z is None:
            return
        kind = z.get("type")
        if kind == "queue":
            i = z["index"]
            if self.view == "queue":
                self.sel["queue"] = i
            tr = self.snap.queue[i] if i < len(self.snap.queue) else None
            if tr is not None:
                self.ensure_view("playlists")
                self.picker = {"track": tr, "sel": 0}
            return
        if kind == "select":
            view, idx = z["view"], z["index"]
            self.sel[view] = idx
            if view != self.view:
                self.goto(view)
            self._open_picker()

    def _click_select(self, z) -> None:
        view, idx = z["view"], z["index"]
        if view != self.view:
            self.goto(view)
            self.sel[view] = idx
            self._last_click = (view, idx, time.monotonic())
            return
        now = time.monotonic()
        last_view, last_idx, last_t = self._last_click
        self.sel[view] = idx
        if last_view == view and last_idx == idx and now - last_t < 0.45:
            self._last_click = (None, None, 0.0)
            self.action_enter()  # double-click = play / open
        else:
            self._last_click = (view, idx, now)

    def _set_volume_at(self, z, x: int) -> None:
        ratio = max(0.0, min(1.0, (x - z["x"]) / max(1, z["w"] - 1)))
        v = int(round(ratio * 100 / 5)) * 5
        self.cfg["volume"] = v
        self.snap.volume = v
        self._call(lambda: self.engine.set_volume(v))

    def _seek_at(self, z, x: int) -> None:
        if not self.snap.track or not self.snap.duration_ms:
            return
        ratio = max(0.0, min(1.0, (x - z["x"]) / max(1, z["w"] - 1)))
        ms = int(ratio * self.snap.duration_ms)
        self.snap.position_ms = ms
        self._call(lambda: self.engine.seek_ms(ms))

    # -- sorting ---------------------------------------------------------
    def sort_label(self, kind: str) -> str:
        if kind not in SORTABLE:
            return ""
        idx = self.sort_idx[kind] % len(SORT_MODES)
        return SORT_MODES[idx][0]

    def _apply_sort(self, kind: str) -> None:
        orig = self.rows_orig.get(kind)
        if orig is None:
            return
        idx = self.sort_idx[kind] % len(SORT_MODES)
        _name, key = SORT_MODES[idx]
        self.rows[kind] = list(orig) if key is None else sorted(orig, key=key)
        self.clamp_sel(kind)

    def cycle_sort(self) -> None:
        kind = self.view
        if kind not in SORTABLE:
            self.toast("sorting works in playlists / liked / album / artist views")
            return
        if not self.rows_orig.get(kind):
            self.toast("nothing to sort yet")
            return
        self.sort_idx[kind] = (self.sort_idx[kind] + 1) % len(SORT_MODES)
        self._apply_sort(kind)
        self.toast(f"sort: {SORT_MODES[self.sort_idx[kind]][0]}")

    # -- list sizing --------------------------------------------------
    def view_count(self) -> int:
        if self.help_visible:
            return 0
        if self.view in ("home", "queue"):
            return len(self.snap.queue)
        if self.view == "playlists":
            return len(self.rows["playlists"]) + 1  # pinned 'liked songs' row
        return len(self.rows.get(self.view, []))

    def clamp_sel(self, kind: str | None = None) -> None:
        kind = kind or self.view
        count = self.view_count_for(kind)
        self.sel[kind] = max(0, min(self.sel[kind], max(0, count - 1)))

    def view_count_for(self, kind: str) -> int:
        if kind in ("home", "queue"):
            return len(self.snap.queue)
        if kind == "playlists":
            return len(self.rows["playlists"]) + 1
        return len(self.rows.get(kind, []))

    # -- key dispatch --------------------------------------------------
    def dispatch(self, ch: str) -> None:
        if self._stop.is_set():
            return
        if self.boot_active():
            self.boot_skip()  # any key during the splash cuts straight to it
            return
        if self.mouse_debug:
            self._last_key = repr(ch)
            self._last_key_t = time.monotonic()
        # ---- typing (search query or new-playlist name)
        if self.typing:
            if ch in ("\r", "\n"):
                if self.typing_target == "playlist":
                    self.submit_new_playlist()
                else:
                    self.submit_search()
            elif ch == K_ESC:
                self.typing = False
                self.type_buf = ""
            elif ch in ("\x08", "\x7f"):
                self.type_buf = self.type_buf[:-1]
            elif ch == K_CTRL_C:
                self.quit()
            elif len(ch) == 1 and ch.isprintable():
                self.type_buf += ch
            return
        # ---- help overlay eats keys
        if self.help_visible:
            self.help_visible = False
            return
        # ---- add-to-playlist picker eats keys
        if self.picker is not None:
            rows = self.rows.get("playlists", [])
            if ch in (K_DOWN, "j"):
                self.picker["sel"] = min(max(0, len(rows) - 1), self.picker["sel"] + 1)
            elif ch in (K_UP, "k"):
                self.picker["sel"] = max(0, self.picker["sel"] - 1)
            elif ch in ("\r", "\n", K_ENTER):
                self._picker_add()
            elif ch in (K_ESC, "q"):
                self.picker = None
            return
        # ---- lyrics overlay just gets out of the way
        if self.show_lyrics and ch in (K_ESC, "L", "?") :
            self.show_lyrics = False
            return
        # ---- global
        if ch in (K_CTRL_C, "q"):
            self.quit()
            return
        if ch == "?":
            self.help_visible = True
            return
        if ch == "/":
            self.view = "search"
            self.typing = True
            self.typing_target = "search"
            self.type_buf = self.search_q or ""
            return
        if ch in (K_ESC,):
            if self.show_stats:
                self.show_stats = False
                return
            self.go_back()
            return
        if ch in ("1", "2", "3", "4", "5", "6", "7", "8"):
            self.goto(VIEW_ORDER[int(ch) - 1])
            return
        if ch == "\t":
            i = VIEW_ORDER.index(self.view if self.view in VIEW_ORDER else "home")
            self.goto(VIEW_ORDER[(i + 1) % len(VIEW_ORDER)])
            return
        if ch == "u":
            self.goto("queue")
            return
        if ch == "m":
            self.goto("devices")
            return
        if ch == "M":
            self.mouse_debug = not self.mouse_debug
            state = "on - click around, watch the footer" if self.mouse_debug else "off"
            if self.mouse_debug and not self.input.mouse_enabled:
                self.toast("mouse diagnostics on - WARNING: mouse reporting inactive (terminal may not support it)", 6)
            else:
                self.toast(f"mouse diagnostics: {state}")
            return
        if ch == "t":
            self.cycle_theme()
            return
        # ---- media transport (run against the engine in the pool)
        if ch == K_SPACE:
            self.snap.playing = not self.snap.playing
            self._call(lambda: self.engine.toggle())
            return
        if ch.lower() == "n":
            self._call(self.engine.next)
            return
        if ch.lower() in ("b", "p"):
            self._call(self.engine.prev)
            return
        if ch in (K_MEDIA_PLAY, K_MEDIA_STOP):
            self._call(lambda: self.engine.toggle())
            return
        if ch == K_MEDIA_NEXT:
            self._call(self.engine.next)
            return
        if ch == K_MEDIA_PREV:
            self._call(self.engine.prev)
            return
        if ch == K_LEFT:
            self._call(lambda: self.engine.seek_step(-5000))
            return
        if ch == K_RIGHT:
            self._call(lambda: self.engine.seek_step(5000))
            return
        if ch in ("+", "="):
            self._vol(5)
            return
        if ch in ("-", "_"):
            self._vol(-5)
            return
        if ch == "s":
            self._call_toggled(self.engine.shuffle_toggle, "shuffle")
            return
        if ch == "r":
            mp = {"off": "off", "context": "all", "track": "one"}
            self._call_toggled(self.engine.repeat_cycle, "repeat", mp)
            return
        if ch == "l":
            self.like_current()
            return
        if ch == "x":
            self.ensure_view(self.view, force=True)
            self.toast("reloading…")
            return
        if ch == "o":
            self.cycle_sort()
            return
        # ---- feature keys
        if ch == ",":
            self._call(lambda: self.engine.seek_step(-30000))
            return
        if ch == ".":
            self._call(lambda: self.engine.seek_step(30000))
            return
        if ch == "L":
            if not self.snap.track:
                self.toast("play something first, then lyrics ♪")
                return
            self.goto("lyrics")
            return
        if ch == "Z":
            self._sleep_cycle()
            return
        if ch == "C":
            self.typing = True
            self.typing_target = "playlist"
            self.type_buf = ""
            self.toast("name your new playlist, then Enter (esc cancels)")
            return
        if ch == "A":
            self._open_picker()
            return
        if ch == "R":
            self._resume_last()
            return
        if ch == "S":
            self.show_stats = not self.show_stats
            if self.show_stats:
                self.show_lyrics = False
            return
        if ch == "N":
            self._queue_selected(to_end=False)
            return
        if ch == "E":
            self._queue_selected(to_end=True)
            return
        if ch == "F":
            self._toggle_duplicates()
            return
        if ch == "d":
            if self.view == "playlist_tracks":
                self._remove_selected()
            elif self.view == "queue":
                self._queue_remove_selected()
            return
        # ---- list navigation
        count = self.view_count()
        if ch in (K_DOWN, "j"):
            self._move(1)
            return
        if ch in (K_UP, "k"):
            self._move(-1)
            return
        if ch == K_PGDN:
            self.sel[self.view] = min(count - 1, self.sel[self.view] + 10) if count else 0
            return
        if ch == K_PGUP:
            self.sel[self.view] = max(0, self.sel[self.view] - 10)
            return
        if ch == "g":
            self.sel[self.view] = 0
            return
        if ch == "G":
            self.sel[self.view] = max(0, count - 1)
            return
        if ch in ("\r", "\n", K_ENTER):
            self.action_enter()
            return
        if ch == "a":
            self.action_play_all()
            return

    def _on_media(self, action: str) -> None:
        """Route a global media-button press to the transport."""
        if self._stop.is_set():
            return
        if action == "play":
            self._call(lambda: self.engine.toggle())
        elif action == "next":
            self._call(self.engine.next)
        elif action == "prev":
            self._call(self.engine.prev)
        elif action == "stop":
            self.snap.playing = False
            self._call(lambda: self.engine.toggle() if self.snap.playing else None)

    def _move(self, delta: int) -> None:
        count = self.view_count()
        if not count:
            return
        new = (self.sel[self.view] + delta) % count
        # sectioned views contain non-selectable section headers - skip them
        if self.view in ("search", "library"):
            rows = self.rows[self.view]
            step = 1 if delta > 0 else -1
            steps = 0
            while steps < count and rows and rows[new][0] == "section":
                new = (new + step) % count
                steps += 1
        self.sel[self.view] = new

    # ------------------------------------------------------------ actions
    def _call(self, fn) -> None:
        """Run an engine action in the pool, then refresh the snapshot."""

        def work():
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                self.toast(f"engine: {exc}")
            self.refresh_now()

        self._pool.submit(work)

    def _call_toggled(self, fn, label, mapping=None) -> None:
        def work():
            try:
                val = fn()
            except Exception as exc:  # noqa: BLE001
                self.toast(f"engine: {exc}")
                return
            if isinstance(val, bool):
                self.toast(f"{label} {'on' if val else 'off'}")
            else:
                self.toast(f"{label} {mapping.get(val, val) if mapping else val}")
            self.refresh_now()

        self._pool.submit(work)

    def _vol(self, delta: int) -> None:
        self.cfg["volume"] = max(0, min(100, int(self.cfg.get("volume", 60)) + delta))
        self.snap.volume = self.cfg["volume"]
        self._call(lambda: self.engine.set_volume(self.cfg["volume"]))

    def like_current(self) -> None:
        tr = self.snap.track
        if not tr:
            self.toast("nothing playing right now")
            return
        flag = not tr.liked

        def work():
            try:
                ok = self.engine.set_liked(tr, flag)
            except Exception as exc:  # noqa: BLE001
                self.toast(f"like failed: {exc}")
                return
            msg = "♥ added to liked songs" if ok else "♡ removed from liked songs"
            # reflect in visible lists that contain this track
            for rows in self.rows.values():
                for row in rows:
                    if getattr(row, "id", None) == tr.id:
                        row.liked = ok
            self.toast(msg)
            self.refresh_now()

        self._pool.submit(work)

    def submit_new_playlist(self) -> None:
        name = self.type_buf.strip()
        self.typing = False
        self.type_buf = ""
        if not name:
            return

        def work():
            try:
                pl = self.engine.create_playlist(name)
            except Exception:
                pl = None
            if not pl:
                self.toast(f"couldn't create '{name}' - log in again to grant playlist write")
                return
            self.toast(f"created playlist '{pl.name}' ♪")
            self.ensure_view("playlists", force=True)
            self._loaded_views.discard("library")
            self.refresh_now()

        self._pool.submit(work)

    # ------------------------------------------------ playlists: add/remove
    def _selected_track(self):
        """Track under the cursor, in any track-shaped view."""
        view, i = self.view, self.sel[self.view]
        if view in ("search", "library"):
            rows = self.rows.get(view, [])
            if rows and i < len(rows) and rows[i][0] == "track":
                return rows[i][1]
            return None
        if view in ("liked", "playlist_tracks", "artist", "album"):
            rows = self.rows.get(view, [])
            if rows and i < len(rows) and isinstance(rows[i], Track):
                return rows[i]
        return None

    def _queue_selected(self, to_end: bool) -> None:
        tr = self._selected_track()
        if tr is None:
            self.toast("hover a track row first (N = play next, E = queue at end)")
            return
        qf = getattr(self.engine, "queue_insert", None)
        if qf is None:
            self.toast("your engine can't edit the queue here")
            return
        self._call(lambda: qf(tr, to_end))

    def _toggle_duplicates(self) -> None:
        """F: fold the current track list down to just the duplicate songs."""
        view = self.view
        if view not in ("liked", "playlist_tracks"):
            self.toast("F works in a playlist or your liked songs")
            return
        rows = self.rows.get(view, [])
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], Track):
            self.toast("load a list first, then press F")
            return
        if not getattr(self, "_dupes_active", False):
            dupes = Catalog.find_duplicates(rows)
            if not dupes:
                self.toast("no duplicate songs in this list ✓")
                return
            self._dupes_orig = list(rows)
            self.rows[view] = dupes
            self._dupes_active = True
            self.clamp_sel(view)
            self.toast(f"showing {len(dupes)} duplicate(s) · press F again to restore", 6)
        else:
            self.rows[view] = self._dupes_orig
            self._dupes_active = False
            self.clamp_sel(view)
            self.toast("restored full list")
        self._apply_sort(view) if getattr(self, "_apply_sort", None) else None

    def _open_picker(self) -> None:
        tr = self._selected_track()
        if tr is None:
            self.toast("hover a track row first, then press A")
            return
        self.ensure_view("playlists")  # make sure the list is warm
        self.picker = {"track": tr, "sel": 0}

    def _picker_add(self) -> None:
        rows = self.rows.get("playlists", [])
        if not self.picker:
            return
        sel = self.picker["sel"]
        if not rows or sel >= len(rows):
            self.picker = None
            return
        pl = rows[sel]
        tr = self.picker["track"]
        self.picker = None

        def work():
            ok = False
            try:
                ok = self.engine.add_to_playlist(pl.id, tr.uri)
            except Exception:
                ok = False
            if ok:
                self.toast(f"added '{tr.name}' → {pl.name} ♪")
                pl.count += 1
            else:
                self.toast("couldn't add (needs write permission / your own playlist)")
            self.refresh_now()

        self._pool.submit(work)

    def _remove_selected(self) -> None:
        pl = self.current_pl
        tr = self._selected_track()
        if pl is None or tr is None:
            return

        def work():
            ok = False
            try:
                ok = self.engine.remove_from_playlist(pl.id, tr.uri)
            except Exception:
                ok = False
            if ok:
                self.toast(f"removed '{tr.name}' from {pl.name}")
                rows = [r for r in self.rows.get("playlist_tracks", [])
                        if getattr(r, "id", None) != tr.id]
                self.rows["playlist_tracks"] = rows
                self.rows_orig["playlist_tracks"] = list(rows)
                self.clamp_sel("playlist_tracks")
            else:
                self.toast("couldn't remove (owner-only, needs write permission)")
            self.refresh_now()

        self._pool.submit(work)

    def _queue_remove_selected(self) -> None:
        "'d' in the queue view: kick the highlighted song out of the line."
        i = self.sel["queue"]
        q = self.snap.queue
        if not q or i >= len(q):
            return
        tr = q[i]
        qr = getattr(self.engine, "queue_remove", None)
        if not callable(qr):
            self.toast("spotify's api can't edit the queue (stream mode can)")
            return

        def work():
            try:
                ok = bool(qr(i))
            except Exception:  # noqa: BLE001
                ok = False
            if ok:
                self.toast(f"kicked '{tr.name}' out of the queue")
                try:  # reflect it instantly, before the next poll lands
                    self.snap.queue.pop(i)
                    self.clamp_sel("queue")
                except Exception:  # noqa: BLE001
                    pass
            else:
                self.toast("couldn't remove that one from the queue")
            self.refresh_now()

        self._pool.submit(work)

    # ------------------------------------------------ sleep timer & resume
    def _sleep_cycle(self) -> None:
        steps = [15, 30, 45, 60, None]
        try:
            cur = steps.index(self._sleep_mins)
        except ValueError:
            cur = -1
        self._sleep_mins = steps[(cur + 1) % len(steps)]
        if self._sleep_mins is None:
            self.sleep_end = None
            self.toast("sleep timer: off")
        else:
            self.sleep_end = time.monotonic() + self._sleep_mins * 60
            self.toast(f"😴 sleep timer: {self._sleep_mins} min")

    def _resume_last(self) -> None:
        offer = self._resume_offer
        if not offer or not offer.get("uri"):
            self.toast("no previous session saved yet - it saves when you quit")
            return
        pos = int(offer.get("pos_ms", 0))
        name = offer.get("name", "")
        mm, ss = pos // 60000, (pos // 1000) % 60
        self.toast(f"resuming '{name}' @ {mm}:{ss:02d}…")
        self._resume_offer = None
        self._call(lambda: self.engine.play_resume(offer["uri"], name, pos))

    def submit_search(self) -> None:
        q = self.type_buf.strip()
        self.typing = False
        if not q:
            return
        self.search_q = q
        self.sel["search"] = 0
        self.scroll["search"] = 0
        self.toast(f"searching: {q}")
        self.loading["search"] = True

        def work():
            try:
                res = self.engine.search_all(q)
            except Exception as exc:  # noqa: BLE001
                self.toast(f"search failed: {exc}")
                res = None
            self.loading["search"] = False
            if not res or not any(res.values()):
                self.rows["search"] = []
                self.toast(f"no results for '{q}'")
                return
            rows = []
            for section, kind in (
                ("ARTISTS", "artist"),
                ("ALBUMS", "album"),
                ("PLAYLISTS", "playlist"),
                ("TRACKS", "track"),
            ):
                bucket = res.get(kind + "s", [])
                cap = {"artist": 6, "album": 6, "playlist": 4, "track": 25}[kind]
                if bucket:
                    rows.append(("section", section))
                    rows.extend((kind, obj) for obj in bucket[:cap])
            self.rows["search"] = rows
            # land the cursor on the first real result, not a header
            for i, r in enumerate(rows):
                if r[0] != "section":
                    self.sel["search"] = i
                    break

        self._pool.submit(work)

    def open_artist(self, artist) -> None:
        self.current_artist = artist
        self.view = "artist"
        self.sel["artist"] = 0
        self.scroll["artist"] = 0
        self.rows.setdefault("artist", [])
        self.toast(f"loading tracks: {artist.name}")
        self._load_list("artist", lambda: self.engine.artist_top(artist))

    def open_album(self, album) -> None:
        self.current_album = album
        self.view = "album"
        self.sel["album"] = 0
        self.scroll["album"] = 0
        self.rows.setdefault("album", [])
        self.toast(f"loading album: {album.name}")
        self._load_list("album", lambda: self.engine.album_tracks(album.id, album))

    def goto(self, view: str) -> None:
        self.view = view
        self.help_visible = False
        self.ensure_view(view)
        self.clamp_sel(view)

    def go_back(self) -> None:
        if self.view == "playlist_tracks":
            self.view = "playlists"
        elif self.view in ("artist", "album"):
            self.view = "search"
        elif self.view != "home":
            self.view = "home"

    def cycle_theme(self) -> None:
        order = config.ORDERED_THEMES
        try:
            i = order.index(self.theme)
        except ValueError:
            i = 0
        self.theme = order[(i + 1) % len(order)]
        self.cfg["theme"] = self.theme
        self.toast(f"theme: {self.theme}")

    def action_enter(self) -> None:
        view = self.view
        i = self.sel[view]
        if view in ("home", "queue"):
            if self.snap.queue and i < len(self.snap.queue):
                qp = getattr(self.engine, "queue_play", None)
                if callable(qp):
                    self._call(lambda: qp(i))
                else:
                    self.toast("jumping inside the queue isn't available in remote mode")
            return
        if view == "playlists":
            if i == 0:
                self.open_liked()
                return
            rows = self.rows["playlists"]
            if rows and i - 1 < len(rows):
                self.open_playlist(rows[i - 1])
            return
        if view == "devices":
            rows = self.rows["devices"]
            if self.engine.mode == "remote" and rows and i < len(rows):
                d = rows[i]
                self.toast(f"switching to {d.get('name')}…")
                self._call(lambda: self.engine.select_device(d))
            return
        if view == "search":
            rows = self.rows["search"]
            if not rows or i >= len(rows):
                return
            kind, obj = rows[i]
            if kind == "section":
                return
            if kind == "artist":
                self.open_artist(obj)
                return
            if kind == "album":
                self.open_album(obj)
                return
            if kind == "playlist":
                self.open_playlist(obj)
                return
            # a track: play it with the search's track section as the queue
            track_rows = [o for k, o in rows if k == "track"]
            idx = track_rows.index(obj)
            self.toast("starting playback…")
            self._call(
                lambda: self.engine.play_tracks(
                    track_rows, idx, f"search: {self.search_q}"
                )
            )
            return
        if view == "library":
            rows = self.rows["library"]
            if not rows or i >= len(rows):
                return
            kind, obj = rows[i]
            if kind == "artist":
                self.open_artist(obj)
                return
            if kind != "track":
                return
            track_rows = [o for k, o in rows if k == "track"]
            idx = track_rows.index(obj)
            self.toast("starting playback…")
            self._call(lambda: self.engine.play_tracks(track_rows, idx, "library"))
            return
        # track lists
        rows = self.rows.get(view, [])
        if not rows or i >= len(rows):
            return
        ctx_name = {
            "liked": "Liked Songs",
            "playlist_tracks": self.current_pl.name if self.current_pl else "playlist",
            "artist": f"Artist: {self.current_artist.name if self.current_artist else '?'}",
            "album": f"Album: {self.current_album.name if self.current_album else '?'}",
        }.get(view, view)
        self.toast("starting playback…")
        self._call(lambda: self.engine.play_tracks(rows, i, ctx_name))

    def action_play_all(self) -> None:
        view = self.view
        if view == "playlists":
            i = self.sel["playlists"]
            if i == 0:
                self.toast("playing Liked Songs…")
                self._load_then_play(lambda: self.engine.get_liked(), "Liked Songs")
            else:
                rows = self.rows["playlists"]
                if rows and i - 1 < len(rows):
                    pl = rows[i - 1]
                    self.toast(f"playing '{pl.name}'…")
                    self._call(lambda: self.engine.play_playlist(pl))
        elif view == "liked":
            self._load_then_play(lambda: self.engine.get_liked(), "Liked Songs")
        elif view in ("search", "playlist_tracks"):
            rows = self.rows.get(view, [])
            if rows:
                self.toast("playing from the top…")
                self._call(lambda: self.engine.play_tracks(rows, 0, "from the top"))

    def _load_then_play(self, fetch, name: str) -> None:
        def work():
            try:
                rows = fetch()
            except Exception as exc:  # noqa: BLE001
                self.toast(f"load failed: {exc}")
                return
            if not rows:
                self.toast("nothing to play")
                return
            try:
                self.engine.play_tracks(rows, 0, name)
            except Exception as exc:  # noqa: BLE001
                self.toast(f"play failed: {exc}")
            self.refresh_now()

        self._pool.submit(work)

    # ------------------------------------------------------------ run
    def quit(self) -> None:
        self._stop.set()

    def run(self) -> None:
        self.engine.start(self.toast)
        self.snap = self.engine.snapshot()
        self.ensure_view("playlists")
        offer = self._resume_offer
        if offer and offer.get("uri"):
            self.toast(
                f"welcome back - press R to resume '{offer.get('name', '?')}' ♪", 6
            )
        self.input.open()
        threading.Thread(target=self._poll_loop, daemon=True, name="poller").start()
        threading.Thread(target=self._input_loop, daemon=True, name="input").start()
        if self._media_enabled:
            self.media_keys.start(self._on_media)

        console = Console()
        try:
            with Live(
                _Frame(self),
                console=console,
                screen=True,
                refresh_per_second=FPS,
                redirect_stdout=False,
                redirect_stderr=False,
            ):
                while not self._stop.is_set():
                    time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            self._quit_cleanup()

    def _quit_cleanup(self) -> None:
        self._stop.set()
        try:
            self.media_keys.stop()
        except Exception:
            pass
        try:
            self.input.close()
        except Exception:
            pass
        self.cfg["theme"] = self.theme
        tr = self.snap.track
        if tr:  # remember the session so 'R' can resume it next launch
            self.cfg["last_session"] = {
                "uri": tr.uri,
                "name": tr.name,
                "pos_ms": int(self.snap.position_ms),
            }
        else:
            self.cfg.pop("last_session", None)
        try:
            self.engine.shutdown()
        except Exception:
            pass
        try:
            vol = getattr(self.engine, "_volume", None) or getattr(self.engine, "_vol", None)
            if vol is not None:
                self.cfg["volume"] = int(vol)
        except Exception:
            pass
        try:
            self.stats.save()
        except Exception:
            pass
        config.save_config(self.cfg)
        self._pool.shutdown(wait=False)
