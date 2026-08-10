from __future__ import annotations

import random
import time
from typing import Callable, List

from .models import Playlist, Snapshot, Track

c = 1000 * 60  # one minute in ms

CATALOG = [
    ("demo01", "Neon Horizon", "Subwave", "Midnight City Drive", 3 * 60_000 + 44_000, True),
    ("demo02", "Chrome Rain", "Vektora", "Grid Runner", 4 * 60_000 + 12_000, False),
    ("demo03", "Sunset Circuit", "Analog Dreams", "Warm Signals", 3 * 60_000 + 21_000, True),
    ("demo04", "Low Orbit", "The Pale Satellites", "Weightless", 5 * 60_000 + 3_000, False),
    ("demo05", "Tape Hiss Morning", "Lo-Fi Sunrise", "Bedroom Sessions", 2 * 60_000 + 47_000, True),
    ("demo06", "Afterglow", "Prisma", "Hologram Hearts", 3 * 60_000 + 58_000, True),
    ("demo07", "Midnight Ramen", "Lo-Fi Sunrise", "Bedroom Sessions", 3 * 60_000 + 10_000, False),
    ("demo08", "VHS Summer", "Vektora", "Grid Runner", 4 * 60_000 + 41_000, True),
    ("demo09", "Glass Towers", "Subwave", "Midnight City Drive", 3 * 60_000 + 5_000, False),
    ("demo10", "Terminal Velocity", "Prisma", "Hologram Hearts", 2 * 60_000 + 52_000, False),
    ("demo11", "Dust & Thunder", "Desert Fox", "Dry Lakes", 6 * 60_000 + 17_000, False),
    ("demo12", "Canyon Echoes", "Desert Fox", "Dry Lakes", 4 * 60_000 + 49_000, True),
    ("demo13", "Blue Hour", "The Pale Satellites", "Weightless", 3 * 60_000 + 33_000, False),
    ("demo14", "Flutterboard", "Analog Dreams", "Warm Signals", 3 * 60_000 + 27_000, False),
    ("demo15", "Night Bus 404", "Lo-Fi Sunrise", "Bedroom Sessions", 3 * 60_000 + 51_000, True),
    ("demo16", "Starlight FM", "Prisma", "Hologram Hearts", 4 * 60_000 + 6_000, False),
]

PLAYLISTS = [
    ("Focus Flow", "termify", ["demo05", "demo07", "demo15", "demo04", "demo13"]),
    ("Gym Hype", "termify", ["demo02", "demo08", "demo10", "demo01", "demo16", "demo06"]),
    ("Chill Evening", "termify", ["demo03", "demo05", "demo07", "demo13", "demo09", "demo15"]),
    ("Road Trip", "termify", ["demo11", "demo12", "demo01", "demo09", "demo14", "demo06", "demo16"]),
]

LIKED = ["demo01", "demo03", "demo05", "demo06", "demo08", "demo12", "demo15"]


def _mk(entry) -> Track:
    tid, name, artists, album, dur, liked = entry
    # Deterministic fake 'added on' date so the date-added sort/column shows.
    n = int(tid.replace("demo", "") or "1")
    added = f"202{2 + n % 5}-{(n % 12) + 1:02d}-{(n % 28) + 1:02d}T00:00:00Z"
    return Track(
        id=tid,
        uri=f"spotify:track:{tid}",
        name=name,
        artists=artists,
        album=album,
        duration_ms=dur,
        image_url=f"demo:{tid}",
        liked=liked,
        added_at=added,
    )


TRACKS = [_mk(e) for e in CATALOG]
BY_ID = {t.id: t for t in TRACKS}


class DemoEngine:
    """Offline engine so you can see the UI before connecting anything."""

    mode = "demo"

    def __init__(self, cfg=None):
        self.cfg = cfg or {}
        self._toast_cb: Callable[[str], None] = lambda m: None
        self._tracks: List[Track] = [BY_ID[i] for i in LIKED]
        self._order = list(range(len(self._tracks)))
        self._pos = 0
        self.context_name = "Liked Songs"
        self.shuffle = False
        self.repeat = "off"
        self._vol = int(self.cfg.get("volume", 65))
        self._playing = True
        self._anchor_ms = 72_000  # start 1:12 in, looks alive on first paint
        self._anchor_t = time.monotonic()

    # ------------------------------------------------------------- start
    def start(self, toast: Callable[[str], None]) -> None:
        self._toast_cb = toast
        toast("demo mode: fake tracks, no audio - run without --demo to connect")

    @property
    def me_name(self) -> str:
        return "demo user"

    @property
    def device_label(self) -> str:
        return "Demo (no audio)"

    # ----------------------------------------------------------- catalog
    def get_playlists(self) -> List[Playlist]:
        return [
            Playlist(
                id=f"demo_pl_{i}",
                uri=f"spotify:playlist:demo_pl_{i}",
                name=name,
                owner=owner,
                count=len(ids),
                image_url=f"demo:pl_{name}",
            )
            for i, (name, owner, ids) in enumerate(PLAYLISTS)
        ]

    def get_playlist_tracks(self, pl: Playlist) -> List[Track]:
        for name, _owner, ids in PLAYLISTS:
            if f"demo_pl_{PLAYLISTS.index((name, _owner, ids))}" == pl.id:
                return [BY_ID[i] for i in ids]
        return []

    def get_liked(self) -> List[Track]:
        return [BY_ID[i] for i in LIKED]

    def search(self, q: str) -> List[Track]:
        q = q.lower()
        return [
            t
            for t in TRACKS
            if q in t.name.lower() or q in t.artists.lower() or q in t.album.lower()
        ]

    def search_all(self, q: str) -> dict:
        from .models import Album, Artist

        q = q.lower().strip()
        if not q:
            return {"artists": [], "albums": [], "playlists": [], "tracks": []}
        artists = [
            Artist(id=f"demo_art:{a}", uri="", name=a, image_url=f"demo:art_{a}")
            for a in sorted({t.artists for t in TRACKS})
            if q in a.lower()
        ]
        albums = [
            Album(
                id=f"demo_alb:{al}",
                uri="",
                name=al,
                artists=next(t.artists for t in TRACKS if t.album == al),
                image_url=f"demo:alb_{al}",
                year="2024",
            )
            for al in sorted({t.album for t in TRACKS})
            if q in al.lower()
        ]
        playlists = [p for p in self.get_playlists() if q in p.name.lower()]
        return {
            "artists": artists[:6],
            "albums": albums[:6],
            "playlists": playlists[:4],
            "tracks": self.search(q),
        }

    def artist_top(self, artist) -> List[Track]:
        name = getattr(artist, "name", None) or str(artist).split(":", 1)[-1]
        return [t for t in TRACKS if t.artists == name] or TRACKS[:6]

    def album_tracks(self, album_id: str, album_meta=None) -> List[Track]:
        name = (album_id.split(":", 1)[-1] if album_id else "") or getattr(
            album_meta, "name", ""
        )
        return [t for t in TRACKS if t.album == name]

    def set_liked(self, track: Track, flag: bool) -> bool:
        track.liked = flag
        if flag and track.id not in LIKED:
            LIKED.append(track.id)
        if not flag and track.id in LIKED:
            LIKED.remove(track.id)
        return flag

    # ---------------------------------------------------- demo extras
    def get_bands(self):
        """Fake-but-lively spectrum so demo mode still dances."""
        import math

        t = time.monotonic()
        out = []
        for i in range(32):
            v = 0.45 + 0.38 * math.sin(t * (1.5 + i * 0.23) + i * 1.1)
            v += 0.18 * math.sin(t * (3.1 + i * 0.11) + i * 2.3)
            if not self._playing:
                v *= 0.15
            out.append(max(0.02, min(1.0, v)))
        return out

    def lyrics_for(self, track):
        """A tiny karaoke-ready theme song so demo lyrics actually move."""
        return {
            "plain": [],
            "source": "lrclib",
            "synced": [
                (0, "♪ ♪ ♪"),
                (3_000, "booting up the terminal"),
                (7_000, "pixels waking up slow"),
                (11_000, "gradient skies on a cathode glow"),
                (15_000, "the bassline hums in dropdown rain"),
                (19_000, "no electrons were harmed making this"),
                (24_000, "termify, termify"),
                (28_000, "spotify, but make it CLI"),
                (33_000, "termify, termify"),
                (37_000, "zero bloat and a cool ASCII sky"),
                (42_000, "♪ by @johnthemailboy ♪"),
            ],
        }

    def recently_played(self) -> List[Track]:
        return [BY_ID[i] for i in
                ["demo08", "demo03", "demo11", "demo01", "demo15", "demo05"]]

    def top_tracks(self) -> List[Track]:
        return [BY_ID[i] for i in
                ["demo01", "demo05", "demo03", "demo16", "demo07", "demo12"]]

    def top_artists(self):
        from .models import Artist

        names = ["Prisma", "Subwave", "Lo-Fi Sunrise", "Vektora", "Desert Fox"]
        return [Artist(id=f"demo_art:{n}", uri="", name=n,
                       image_url=f"demo:art_{n}") for n in names]

    def create_playlist(self, name: str):
        PLAYLISTS.append((name, "termify", []))
        i = len(PLAYLISTS) - 1
        return Playlist(id=f"demo_pl_{i}", uri=f"spotify:playlist:demo_pl_{i}",
                        name=name, owner="termify", count=0,
                        image_url=f"demo:pl_{name}")

    def _find_playlist(self, playlist_id: str):
        try:
            idx = int(str(playlist_id).rsplit("_", 1)[-1])
            return PLAYLISTS[idx]
        except Exception:
            return None

    def add_to_playlist(self, playlist_id: str, track_uri: str) -> bool:
        pl = self._find_playlist(playlist_id)
        if pl is None:
            return False
        tid = track_uri.split(":")[-1]
        if tid in BY_ID and tid not in pl[2]:
            pl[2].append(tid)
        return True

    def remove_from_playlist(self, playlist_id: str, track_uri: str) -> bool:
        pl = self._find_playlist(playlist_id)
        if pl is None:
            return False
        tid = track_uri.split(":")[-1]
        if tid in pl[2]:
            pl[2].remove(tid)
        return True

    # ---------------------------------------------------------- playback
    def play_tracks(self, tracks, index, context_name) -> None:
        self._tracks = list(tracks)
        if self.shuffle:
            rest = [i for i in range(len(tracks)) if i != index]
            random.shuffle(rest)
            self._order = [index] + rest
        else:
            self._order = [index] + [i for i in range(len(tracks)) if i != index]
        self._pos = 0
        self.context_name = context_name
        self._playing = True
        self._reset_clock(0)

    def play_playlist(self, pl: Playlist) -> None:
        tracks = self.get_playlist_tracks(pl)
        if tracks:
            self.play_tracks(tracks, 0, pl.name)

    def play_resume(self, uri: str, name: str, pos_ms: int) -> None:
        tr = BY_ID.get(uri.split(":")[-1]) or TRACKS[0]
        self.play_tracks([tr], 0, "resumed session")
        self._reset_clock(max(0, int(pos_ms)))

    def _current(self):
        if not self._order:
            return None
        return self._tracks[self._order[self._pos]]

    def _reset_clock(self, pos_ms: int) -> None:
        self._anchor_ms = pos_ms
        self._anchor_t = time.monotonic()

    def _position(self) -> int:
        if self._playing:
            return self._anchor_ms + int((time.monotonic() - self._anchor_t) * 1000)
        return self._anchor_ms

    # ------------------------------------------------------------ control
    def toggle(self) -> None:
        pos = self._position()
        self._playing = not self._playing
        self._reset_clock(pos)

    def next(self) -> None:
        if self._pos + 1 < len(self._order):
            self._pos += 1
        elif self.repeat == "context":
            self._pos = 0
        else:
            self._toast_cb("end of the list")
            return
        self._reset_clock(0)
        self._playing = True

    def prev(self) -> None:
        if self._position() > 3000:
            self.seek_ms(0)
            return
        if self._pos > 0:
            self._pos -= 1
            self._reset_clock(0)

    def queue_play(self, index: int) -> None:
        target = self._pos + 1 + index
        if target < len(self._order):
            self._pos = target
            self._reset_clock(0)
            self._playing = True

    def queue_remove(self, index: int) -> bool:
        target = self._pos + 1 + index
        if 0 <= target < len(self._order):
            self._order.pop(target)
            return True
        return False

    def seek_ms(self, ms: int) -> None:
        t = self._current()
        if t:
            self._reset_clock(max(0, min(int(ms), t.duration_ms - 1000)))

    def seek_step(self, delta_ms: int) -> None:
        self.seek_ms(self._position() + delta_ms)

    def set_volume(self, v: int) -> None:
        self._vol = max(0, min(100, int(v)))

    def volume_step(self, delta: int) -> None:
        self.set_volume(self._vol + delta)

    def shuffle_toggle(self) -> bool:
        self.shuffle = not self.shuffle
        cur = self._order[self._pos]
        rest = [i for i in range(len(self._tracks)) if i != cur]
        if self.shuffle:
            random.shuffle(rest)
        self._order = [cur] + rest
        self._pos = 0
        return self.shuffle

    def repeat_cycle(self) -> str:
        modes = ["off", "context", "track"]
        self.repeat = modes[(modes.index(self.repeat) + 1) % 3]
        return self.repeat

    # --------------------------------------------------------------- poll
    def snapshot(self) -> Snapshot:
        track = self._current()
        if track and self._position() >= track.duration_ms:
            # auto-advance like a real player
            if self.repeat == "track":
                self.seek_ms(0)
            elif self._pos + 1 < len(self._order) or self.repeat == "context":
                self.next()
            else:
                self._playing = False
                self._anchor_ms = track.duration_ms
        queue = [
            self._tracks[self._order[i]]
            for i in range(self._pos + 1, min(self._pos + 101, len(self._order)))
        ]
        pos = self._position()
        if track:
            pos = min(pos, track.duration_ms)
        return Snapshot(
            track=track,
            playing=self._playing,
            position_ms=pos,
            volume=self._vol,
            shuffle=self.shuffle,
            repeat=self.repeat,
            context_name=self.context_name,
            queue=queue,
            status="playing" if self._playing else "paused",
            device_label=self.device_label,
        )

    def shutdown(self) -> None:
        pass
