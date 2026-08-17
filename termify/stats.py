"""Local listening statistics.

Keeps a tiny, offline record of what you play (counts + seconds listened)
keyed by calendar day, so Termify can show a stats view and a weekly
'your week in music' report without phoning home anywhere.

Storage: ~/.termify/stats.json  (a plain dict, designed to be robust if
it ever gets corrupted - a bad file just means stats reset, never a crash).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .models import Track

_DAY = 86400.0


class Stats:
    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, Any] = self._load()

    # ------------------------------------------------------------ loading
    def _load(self) -> Dict[str, Any]:
        try:
            if self.path.exists():
                d = json.loads(self.path.read_text())
                if isinstance(d, dict) and "days" in d:
                    return d
        except Exception:
            pass
        return {
            "since": date.today().isoformat(),
            "days": {},       # "2026-08-10" -> {"ms": int, "tracks": {uri: {...}}}
        }

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data))
        except Exception:
            pass

    # ------------------------------------------------------------ recording
    def add_play(self, track: Track, ms: int) -> None:
        """Record listening for one track (seconds, not counts)."""
        if not track or ms <= 0:
            return
        day = date.today().isoformat()
        dayd = self.data["days"].setdefault(day, {"ms": 0, "tracks": {}})
        dayd["ms"] = dayd.get("ms", 0) + int(ms)
        tr = dayd["tracks"].setdefault(
            track.uri,
            {"name": track.name, "artists": track.artists, "ms": 0},
        )
        tr["ms"] = tr.get("ms", 0) + int(ms)

    # ------------------------------------------------------------ helpers
    def _day_ms(self, day: str) -> int:
        return int(self.data["days"].get(day, {}).get("ms", 0))

    def _days(self, n: int) -> List[str]:
        today = date.today()
        return [(today - timedelta(days=i)).isoformat() for i in range(n)]

    # ------------------------------------------------------------ queries
    def ms_today(self) -> int:
        return self._day_ms(date.today().isoformat())

    def ms_period(self, n_days: int) -> int:
        return sum(self._day_ms(d) for d in self._days(n_days))

    def ms_all(self) -> int:
        return sum(d.get("ms", 0) for d in self.data["days"].values())

    def streak_days(self) -> int:
        """Consecutive days (ending today) with at least one second played."""
        streak = 0
        today = date.today()
        for i in range(0, 365):
            day = (today - timedelta(days=i)).isoformat()
            if self._day_ms(day) > 0:
                streak += 1
            elif i == 0:
                continue  # today may not have data yet; don't break the streak
            else:
                break
        return streak

    def top_tracks(self, n: int = 5, n_days: int = 7) -> List[Tuple[str, str, int]]:
        """Most-played (name, artists, seconds) over the last n_days."""
        agg: Dict[str, Dict[str, Any]] = {}
        for day in self._days(n_days):
            for uri, tr in self.data["days"].get(day, {}).get("tracks", {}).items():
                a = agg.setdefault(uri, {"name": tr.get("name", "?"),
                                         "artists": tr.get("artists", ""),
                                         "ms": 0})
                a["ms"] += tr.get("ms", 0)
        ordered = sorted(agg.values(), key=lambda x: x["ms"], reverse=True)
        return [(a["name"], a["artists"], int(a["ms"])) for a in ordered[:n]]

    def top_artists(self, n: int = 5, n_days: int = 7) -> List[Tuple[str, int]]:
        agg: Dict[str, int] = {}
        for day in self._days(n_days):
            for tr in self.data["days"].get(day, {}).get("tracks", {}).values():
                for artist in (tr.get("artists", "") or "").split(", "):
                    if artist:
                        agg[artist] = agg.get(artist, 0) + tr.get("ms", 0)
        ordered = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
        return ordered[:n]

    # ------------------------------------------------------------ report
    def weekly_report(self) -> Dict[str, Any]:
        """A compact 'your week in music' digest."""
        n = 7
        return {
            "minutes": self.ms_period(n) // 60000,
            "top_tracks": self.top_tracks(5, n),
            "top_artists": self.top_artists(5, n),
            "streak": self.streak_days(),
            "since": self.data.get("since", ""),
        }


def fmt_ms(ms: int) -> str:
    """1234567 -> '20m 34s'  (hours shown when large)."""
    total = max(0, int(ms)) // 1000
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"
