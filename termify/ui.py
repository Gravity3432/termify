from __future__ import annotations

import colorsys
import math
import random
import time as _time
from typing import List, Optional, Tuple

from rich import box
from rich.align import Align
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from .lyrics import current_index as lyric_index
from .models import Snapshot, Track
from .stats import fmt_ms

# ------------------------------------------------------------------ themes
# tuple = classic sweep (base hue, hue span to sweep through, period in sec)
# dict  = richer theme; `mode: "rainbow"` cycles the full hue wheel forever,
#         `pulse` makes highlights breathe, sat/light override the defaults.
THEMES = {
    # -- the classic originals -------------------------------------------
    "aurora":  (130, 150, 26.0),
    "sunset":  (350, 65, 20.0),
    "ocean":   (170, 75, 22.0),
    "candy":   (275, 70, 17.0),
    "vampire": (330, 40, 15.0),  # night-violet draining into blood red
    "mono":    (158, 0, 9999.0),

    # -- the bold maximalist additions -----------------------------------
    "chroma":   {"mode": "rainbow", "speed": 14.0, "sat": 0.95, "light": 0.68},
    "rainbow":  {"mode": "rainbow", "speed": 26.0, "sat": 1.00, "light": 0.66},
    "neon":     {"mode": "rainbow", "speed": 20.0, "sat": 1.00, "light": 0.70,
                 "pulse": True},
    "synthwave": {"base": 285, "span": 75, "period": 14.0, "pulse": True,
                  "sat": 1.0, "light": 0.66},   # magenta->cyan synth 80s
    "toxic":    {"mode": "rainbow", "speed": 11.0, "sat": 1.0, "light": 0.60},
    "inferno":  {"base": 0, "span": 55, "period": 9.0, "sat": 1.0,
                 "light": 0.62, "pulse": True},  # flames
    "ice":      {"base": 195, "span": 60, "period": 18.0, "sat": 0.75,
                 "light": 0.66},
    "gold":     {"base": 45, "span": 30, "period": 20.0, "sat": 0.95,
                 "light": 0.62},
    "plasma":   {"base": 320, "span": 60, "period": 12.0, "sat": 1.0,
                 "light": 0.60, "pulse": True},
}

BIG_LOGO = [
    "████████╗███████╗██████╗ ███╗   ███╗██╗███████╗██╗   ██╗",
    "╚══██╔══╝██╔════╝██╔══██╗████╗ ████║██║██╔════╝╚██╗ ██╔╝",
    "   ██║   █████╗  ██████╔╝██╔████╔██║██║█████╗   ╚████╔╝ ",
    "   ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║██║██╔══╝    ╚██╔╝  ",
    "   ██║   ███████╗██║  ██║██║ ╚═╝ ██║██║██║        ██║   ",
    "   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝        ╚═╝   ",
]
# dripping-blood letters (classic "Bloody" figlet face) for vampire mode
BIG_LOGO_BLOODY = [
    line.rstrip()
    for line in (
        "▄▄▄█████▓▓█████  ██▀███   ███▄ ▄███▓ ██▓  █████▒▓██   ██▓",
        "▓  ██▒ ▓▒▓█   ▀ ▓██ ▒ ██▒▓██▒▀█▀ ██▒▓██▒▓██   ▒  ▒██  ██▒",
        "▒ ▓██░ ▒░▒███   ▓██ ░▄█ ▒▓██    ▓██░▒██▒▒████ ░   ▒██ ██░",
        "░ ▓██▓ ░ ▒▓█  ▄ ▒██▀▀█▄  ▒██    ▒██ ░██░░▓█▒  ░   ░ ▐██▓░",
        "  ▒██▒ ░ ░▒████▒░██▓ ▒██▒▒██▒   ░██▒░██░░▒█░      ░ ██▒▓░",
        "  ▒ ░░   ░░ ▒░ ░░ ▒▓ ░▒▓░░ ▒░   ░  ░░▓   ▒ ░       ██▒▒▒ ",
        "    ░     ░ ░  ░  ░▒ ░ ▒░░  ░      ░ ▒ ░ ░       ▓██ ░▒░ ",
        "  ░         ░     ░░   ░ ░      ░    ▒ ░ ░ ░     ▒ ▒ ░░  ",
        "            ░  ░   ░            ░    ░           ░ ░     ",
        "                                                 ░ ░     ",
    )
]

TAGLINE = "spotify · zero bloat · pure terminal"
VAMPIRE_TAGLINE = "🦇 dine in the dark · zero bloat · pure terminal"


def banner_for(theme: str) -> List[str]:
    return BIG_LOGO_BLOODY if theme == "vampire" else BIG_LOGO


# ------------------------------------------------------------------ boot splash
SPLASH_ART = [line.rstrip() for line in (
    "     ██╗████████╗███╗   ███╗██████╗ ",
    "     ██║╚══██╔══╝████╗ ████║██╔══██╗",
    "     ██║   ██║   ██╔████╔██║██████╔╝",
    "██   ██║   ██║   ██║╚██╔╝██║██╔══██╗",
    "╚█████╔╝   ██║   ██║ ╚═╝ ██║██████╔╝",
    " ╚════╝    ╚═╝   ╚═╝     ╚═╝╚═════╝ ",
)]

SPLASH_ART_BLOODY = [line.rstrip() for line in (
    " ▄▄▄██▀▀▀▄▄▄█████▓ ███▄ ▄███▓ ▄▄▄▄   ",
    "   ▒██   ▓  ██▒ ▓▒▓██▒▀█▀ ██▒▓█████▄ ",
    "   ░██   ▒ ▓██░ ▒░▓██    ▓██░▒██▒ ▄██",
    "▓██▄██▓  ░ ▓██▓ ░ ▒██    ▒██ ▒██░█▀  ",
    " ▓███▒     ▒██▒ ░ ▒██▒   ░██▒░▓█  ▀█▓",
    " ▒▓▒▒░     ▒ ░░   ░ ▒░   ░  ░░▒▓███▀▒",
    " ▒ ░▒░       ░    ░  ░      ░▒░▒   ░ ",
    " ░ ░ ░     ░      ░      ░    ░    ░ ",
    " ░   ░                   ░    ░      ",
    "                                     ",
)]
SPLASH_SUB = "J O H N · T H E · M A I L · B O Y"
SPLASH_BY = "made with ♥ by @johnthemailboy"
SPLASH_GLYPHS = "▓▒░╳¤#%§¶*+=~^ΞΔ"


def _cheap_hash(*nums) -> int:
    h = 0
    for n in nums:
        h = (h * 131 + int(n)) & 0x7FFFFFFF
    return h


def render_splash(app, width: int, height: int, t: Optional[float] = None) -> Panel:
    """Boot sequence: neon rain + JTMB letters scrambling into focus,
    then his name types itself underneath. Any key skips it."""
    theme = app.theme
    t = app.boot_t() if t is None else t
    W = max(40, width - 4)
    H = max(16, height - 4)
    art = SPLASH_ART_BLOODY if theme == "vampire" else SPLASH_ART
    art = [l.ljust(max(len(x) for x in art)) for l in art]
    art_h, art_w = len(art), len(art[0])
    tick = int(t * 12)

    top = max(0, (H - art_h - 6) // 2)
    x0 = max(0, (W - art_w) // 2)
    sub_y = top + art_h + 2
    by_y = sub_y + 2

    rows = []  # each row: list of [char, style] cells we can overwrite
    for y in range(H):
        line = []
        for x in range(W):
            ch, style = " ", ""
            # neon rain backdrop: each column has a fixed offset/tail; only
            # the head's position moves over time.
            hh = _cheap_hash(x, 17)
            span = H * 2
            head = (tick * 7 + hh % span) % span
            drop = head - y
            if 0 <= drop <= 5 and (hh // 13) % 3 == 0:
                g = SPLASH_GLYPHS[_cheap_hash(x, y, tick) % len(SPLASH_GLYPHS)]
                light = max(0.05, 0.30 - drop * 0.05)
                ch, style = g, theme_color(theme, t, phase=x * 0.05,
                                           light=light, sat=0.7)
            line.append([ch, style])
        rows.append(line)

    # the letters: every cell has a "birth moment"; before it we show cycling
    # glitch glyphs, at it we flash white, after it the real char.
    for ly, art_line in enumerate(art):
        row = rows[top + ly] if 0 <= top + ly < len(rows) else None
        if row is None:
            break
        for lx, ch in enumerate(art_line):
            x = x0 + lx
            if ch == " " or x >= W:
                continue
            birth = 0.15 + 1.5 * (lx / art_w) + _cheap_hash(lx, ly) % 40 / 100.0
            fade = t - birth
            if fade < 0:
                row[x] = [" ", ""]
            elif fade < 0.45:
                g = SPLASH_GLYPHS[_cheap_hash(lx, ly, tick) % len(SPLASH_GLYPHS)]
                row[x] = [g, theme_color(theme, t, phase=lx * 0.1, light=0.55)]
            else:
                light = 0.78 if fade < 0.8 else 0.66 - 0.09 * math.sin(t * 2.2)
                row[x] = [ch, theme_color(theme, t, phase=lx * 0.09,
                                          light=light, sat=0.88)]

    # typewriter subline
    if t > 0.9 and 0 <= sub_y < H:
        typed = int((t - 0.9) * 24)
        text = SPLASH_SUB[: max(0, min(typed, len(SPLASH_SUB)))]
        cursor = "▌" if typed < len(SPLASH_SUB) else ""
        start = max(0, (W - len(SPLASH_SUB)) // 2)
        for i, c in enumerate(text + cursor):
            if start + i < W:
                rows[sub_y][start + i] = [
                    c, "bold grey90" if c != "▌"
                    else theme_color(theme, t, light=0.65)]
    # the credit line (cool kids sign their work)
    if t > 2.0 and 0 <= by_y < H:
        start = max(0, (W - len(SPLASH_BY)) // 2)
        light = 0.45 + 0.15 * math.sin(t * 3.0)
        for i, c in enumerate(SPLASH_BY):
            if start + i < W:
                rows[by_y][start + i] = [
                    c, theme_color(theme, t, phase=i * 0.2, light=light)]
    if t > 2.4 and H - 2 >= 0:
        hint = "[ press any key ]"
        if int(t * 2.5) % 2 == 0:
            base = max(0, W - len(hint) - 1)
            for i, c in enumerate(hint):
                if base + i < W:
                    rows[H - 2][base + i] = [c, "grey37"]
        brand = "♪ TERMIFY"
        for i, c in enumerate(brand):
            if i < W:
                rows[H - 2][i] = [c, theme_color(theme, t, phase=i * 0.4,
                                                 light=0.5)]

    body = Text()
    for i, line in enumerate(rows):
        if i:
            body.append("\n")
        for ch, style in line:
            body.append(ch, style=style)
    return Panel(body, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.30),
                 padding=(0, 0))

KEY_LEGEND = " space · n/b skip · u queue · l like · ? all keys · q quit"


def theme_params(name: str):
    return THEMES.get(name, THEMES["aurora"])


def theme_color(theme: str, t: float, phase: float = 0.0,
                light: float = 0.62, sat: float = 0.80) -> str:
    """Animated color for a theme.

    Themes can be a tuple `(base, span, period)` (classic sweep) or a dict with
    extras: `mode: 'rainbow'` cycles the full hue wheel forever, and `pulse`
    oscillates the lightness so highlights breathe.
    """
    p = theme_params(theme)
    if isinstance(p, tuple):
        base, span, period = p
        if span == 0:
            hue = base
        else:
            w = 0.5 + 0.5 * math.sin(2 * math.pi * (t / period) + phase)
            hue = base + span * w
        hue %= 360
    else:
        base = p.get("base", 130)
        if p.get("mode") == "rainbow":
            speed = p.get("speed", 18.0)
            hue = (t * speed + phase * 40 + base) % 360
        else:
            span = p.get("span", 70)
            period = p.get("period", 22.0)
            w = 0.5 + 0.5 * math.sin(2 * math.pi * (t / period) + phase)
            hue = (base + span * w) % 360
        if p.get("pulse"):
            light = light * (0.82 + 0.18 * math.sin(t * 4.0 + phase * 2))
        sat = p.get("sat", sat)
        light = p.get("light", light)
    light = max(0.0, min(1.0, light))
    sat = max(0.0, min(1.0, sat))
    r, g, b = colorsys.hls_to_rgb((hue % 360) / 360.0, light, sat)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def sel_accent(theme: str, t: float, light: float = 0.58) -> str:
    """Pulsing selection background - bolder & alive."""
    l = light + 0.10 * math.sin(t * 4.5)
    return theme_color(theme, t, light=max(0.45, min(0.8, l)), sat=0.9)


def panel_border(theme: str, t: float, light: float = 0.55) -> str:
    """A bolder, breathing border color for the maximalist look."""
    l = light + 0.12 * math.sin(t * 3.2)
    return theme_color(theme, t, light=max(0.4, min(0.85, l)), sat=0.92)


def gradient_text(s: str, theme: str, t: float, step: float = 0.23,
                  light: float = 0.62, bold: bool = True) -> Text:
    out = Text()
    for i, ch in enumerate(s):
        style = theme_color(theme, t, phase=i * step, light=light)
        out.append(ch, style=("bold " if bold else "") + style)
    return out


def gradient_lines(lines: List[str], theme: str, t: float) -> Text:
    out = Text()
    for li, line in enumerate(lines):
        for i, ch in enumerate(line):
            out.append(
                ch, style=theme_color(theme, t, phase=i * 0.10 + li * 0.55)
            )
        out.append("\n")
    return out


# ------------------------------------------------------------------ widgets

def bar(width: int, ratio: float, theme: str, t: float,
        tail: bool = True, pulse: bool = True) -> Text:
    """A horizontal progress/volume bar with a travelling gradient."""
    width = max(4, width)
    ratio = max(0.0, min(1.0, ratio))
    filled = int(round(width * ratio))
    head = filled - 1
    out = Text()
    for i in range(width):
        if i < filled:
            l = 0.66 if (pulse and i == head and 0.5 + 0.5 * math.sin(t * 6) > 0.5) else 0.52
            out.append("█", style=theme_color(theme, t, phase=i * 0.12, light=l, sat=0.85))
        elif tail:
            out.append("░", style="grey23")
    return out


def marquee(s: str, width: int, t: float, speed: float = 3.0) -> str:
    if len(s) <= width or width <= 6:
        return s.ljust(width)
    gap = 6
    span = len(s) + gap
    off = int(t * speed) % span
    buf = (s + " " * gap + s + " " * gap)
    return buf[off : off + width]


def visualizer(seed: str, cols: int, rows: int, t: float,
               playing: bool, theme: str,
               bands: Optional[List[float]] = None) -> Text:
    """Spectrum bars - driven by the REAL audio FFT when bands are given
    (stream mode), otherwise clock vibes (remote mode has no local audio)."""
    cols = max(6, cols)
    rows = max(2, rows)
    out = Text()
    levels = []
    if bands:
        n = len(bands)
        for c in range(cols):
            v = bands[min(n - 1, int(c * n / cols))]
            if not playing:
                v *= 0.25
            levels.append(int(round(max(0.02, min(1.0, v)) * rows)))
    else:
        rng = random.Random(seed or "termify")
        col_cfg = [(rng.uniform(0.7, 2.6), rng.uniform(0, 6.28), rng.uniform(0.45, 1.0))
                   for _ in range(cols)]
        for speed, phase, amp in col_cfg:
            v = amp * (0.62 + 0.38 * math.sin(t * speed + phase))
            v += 0.22 * math.sin(t * speed * 2.33 + phase * 2)
            if not playing:
                v *= 0.22 + 0.08 * math.sin(t * 0.8 + phase)
            v = max(0.02, min(1.0, v))
            levels.append(int(round(v * rows)))
    for r in range(rows, 0, -1):
        line = Text()
        for c_i, lvl in enumerate(levels):
            if lvl >= r:
                depth = r / rows
                line.append(
                    "█",
                    style=theme_color(theme, t, phase=c_i * 0.30 + depth * 2.2,
                                      light=0.45 + 0.25 * depth, sat=0.85),
                )
            else:
                line.append(" ", style="")
        out.append_text(line)
        out.append("\n")
    return out


def truncate(s: str, width: int) -> str:
    if width <= 1:
        return ""
    return s if len(s) <= width else s[: width - 1] + "…"


def dur_text(ms: int) -> str:
    total = max(0, ms // 1000)
    return f"{total // 60}:{total % 60:02d}"


def window(app, kind: str, avail: int, count: int) -> int:
    """Keep the selection inside the visible window; returns scroll offset."""
    sel = max(0, min(app.sel[kind], max(0, count - 1)))
    app.sel[kind] = sel
    sc = app.scroll[kind]
    if sel < sc:
        sc = sel
    elif sel >= sc + avail:
        sc = sel - avail + 1
    sc = max(0, min(sc, max(0, count - avail)))
    app.scroll[kind] = sc
    return sc


# ------------------------------------------------------------------ rows

def track_row(track: Track, idx: int, selected: bool, width: int,
              theme: str, t: float, date_col: bool = False) -> Text:
    heart = "♥" if track.liked else " "
    dur = track.duration_text
    num = f"{idx + 1:>3}"
    fixed = 3 + 1 + 1 + 1 + len(dur) + 2 + 3  # num+heart+spaces+dur+seps
    avail = max(10, width - fixed)
    title_w = max(12, int(avail * 0.48))
    artist_w = max(8, int(avail * 0.30))
    album_w = max(0, avail - title_w - artist_w - 2)

    out = Text()
    caret = "❯" if selected else " "
    title_part = truncate(track.name, title_w).ljust(title_w)
    artist_part = truncate(track.artists, artist_w).ljust(artist_w)
    # When sorting by date added, show the date in the album slot.
    meta = track.date_text if date_col else track.album
    album_part = truncate(meta, album_w).ljust(album_w) if album_w >= 6 else ""
    if selected:
        accent = theme_color(theme, t, light=0.55)
        out.append(f"{caret} ", style=f"bold black on {accent}")
        body = f"{num} {heart} {title_part} {artist_part} {album_part}{dur}"
        out.append(body.ljust(width - 2), style=f"bold black on {accent}")
    else:
        out.append(f"{caret} ", style="grey30")
        out.append(f"{num} ", style="grey35")
        out.append(f"{heart} ", style=theme_color(theme, t, phase=idx * 0.4) if track.liked else "grey27")
        out.append(title_part, style="white")
        out.append(" ", style="")
        out.append(artist_part, style="grey62")
        if album_part:
            out.append(" ", style="")
            out.append(album_part, style="grey42")
            out.append(" ", style="")
        out.append(dur, style="grey58")
    return out


def playlist_row(pl, idx: int, selected: bool, width: int, theme: str, t: float) -> Text:
    count = f"{pl.count} tracks"
    out = Text()
    caret = "❯" if selected else " "
    num = f"{idx + 1:>3}"
    name_w = max(10, width - 3 - 2 - len(count) - 2 - len(pl.owner) - 3)
    if selected:
        accent = theme_color(theme, t, light=0.55)
        body = f"{num} {truncate(pl.name, name_w).ljust(name_w)}  {pl.owner:<10.10} {count}"
        out.append(f"{caret} ", style=f"bold black on {accent}")
        out.append(body.ljust(width - 2), style=f"bold black on {accent}")
    else:
        out.append(f"{caret} ", style="grey30")
        out.append(f"{num} ", style="grey35")
        out.append(truncate(pl.name, name_w).ljust(name_w), style="white")
        out.append("  ", style="")
        out.append(f"{pl.owner:<10.10}"[:10], style="grey50")
        out.append(" " + count, style="grey58")
    return out


def device_row(dev: dict, idx: int, selected: bool, active: bool, width: int,
               theme: str, t: float) -> Text:
    name = dev.get("name", "?")
    dtype = dev.get("type", "")
    out = Text()
    caret = "❯" if selected else " "
    dot = "●" if active else "○"
    body = f"{dot} {name}  ({dtype})"
    if selected:
        accent = theme_color(theme, t, light=0.55)
        out.append(f"{caret} ", style=f"bold black on {accent}")
        out.append(truncate(body, width - 4).ljust(width - 2), style=f"bold black on {accent}")
    else:
        out.append(f"{caret} ", style="grey30")
        out.append(truncate(body, width - 4), style="white" if active else "grey62")
    return out


# ------------------------------------------------------------------ pieces

def render_header(app, width: int, big: bool) -> Panel:
    theme, t = app.theme, app.t()
    tagline = VAMPIRE_TAGLINE if theme == "vampire" else TAGLINE
    if big:
        logo = gradient_lines(banner_for(theme), theme, t)
        right = Text()
        right.append("\n")
        if theme == "vampire":
            right.append("\n\n")  # taller banner - keep the side block centered
        right.append("  ♪ " + app.engine.me_name + "\n", style="bold white")
        right.append("  " + tagline + "\n", style="grey42")
        right.append("  by ", style="grey42")
        right.append("@johnthemailboy\n", style=f"bold {theme_color(theme, t, phase=1.7)}")
        right.append("  mode ", style="grey42")
        right.append(app.engine.mode, style=theme_color(theme, t, phase=1.1))
        right.append("  ·  theme ", style="grey42")
        right.append(theme, style=theme_color(theme, t, phase=2.3))
        from rich.columns import Columns

        content = Columns([logo, right], expand=True, padding=(0, 2))
    else:
        title = gradient_text(" ♪ T E R M I F Y ♪ ", theme, t, step=0.35)
        title.append(f"   {tagline}", style="grey42")
        content = title
    return Panel(content, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40),
                 padding=(0, 1))


def render_nav(app, x0: int, y0: int, height: int) -> Panel:
    theme, t = app.theme, app.t()
    items = [
        ("home", "1", "Home"),
        ("search", "2", "Search"),
        ("playlists", "3", "Playlists"),
        ("liked", "4", "Liked ♥"),
        ("library", "5", "Library"),
        ("devices", "6", "Devices"),
        ("queue", "7", "Queue ♫"),
        ("lyrics", "8", "Lyrics 🎤"),
        ("settings", "9", "Settings ⚙"),
    ]
    out = Text()
    out.append(" NAVIGATE\n", style="bold grey50")
    out.append("─" * 20 + "\n", style="grey27")
    active = {
        "playlist_tracks": "playlists",
        "artist": "search",
        "album": "search",
    }.get(app.view, app.view)
    for i, (key, num, label) in enumerate(items):
        sel = active == key
        app.add_zone(x0 + 1, y0 + 2 + i, 20, 1, type="nav", view=key)
        if sel:
            accent = theme_color(theme, t, light=0.55)
            out.append(f" ❯ [{num}] {label}\n", style=f"bold black on {accent}")
        else:
            out.append(f"   [{num}] {label}\n", style="grey70")
    # ---- collapsible playlist drawer (stays on Home; [ opens it)
    if getattr(app, "side_drawer", False):
        pls = app.rows.get("playlists", [])
        out.append("\n PLAYLISTS ▾\n", style=f"bold {theme_color(theme, t, light=0.6)}")
        out.append("─" * 20 + "\n", style="grey27")
        avail = max(3, height - 22)          # rows we can show in the drawer
        if not pls and app.loading.get("playlists"):
            out.append(" loading…\n", style="grey50")
        elif not pls:
            out.append(" (none yet)\n", style="grey35")
        else:
            sc = app._drawer_scroll
            if app.drawer_sel < sc:
                sc = app.drawer_sel
            if app.drawer_sel >= sc + avail:
                sc = app.drawer_sel - avail + 1
            sc = max(0, min(sc, max(0, len(pls) - avail)))
            app._drawer_scroll = sc
            for k in range(sc, min(len(pls), sc + avail)):
                pl = pls[k]
                app.add_zone(x0 + 1, y0 + 13 + k - sc, 20, 1,
                             type="drawer", index=k)
                if k == app.drawer_sel:
                    accent = theme_color(theme, t, light=0.55)
                    out.append(f" ❯ {truncate(pl.name, 18).ljust(18)}\n",
                               style=f"bold black on {accent}")
                else:
                    out.append(f"   {truncate(pl.name, 18)}\n", style="grey70")
            if len(pls) > sc + avail:
                out.append(f"   …{len(pls) - sc - avail} more\n", style="grey35")
        out.append(" [esc] close · [enter] play\n", style="grey37")
    else:
        out.append("\n")
        out.append(" DEVICE\n", style="bold grey50")
        out.append("─" * 20 + "\n", style="grey27")
        out.append(" " + truncate("♪ " + app.snap.device_label, 19) + "\n", style=theme_color(theme, t, light=0.5))
    if app.snap.device_label and app.engine.mode == "remote":
        out.append(" press [6] to switch\n", style="grey37")
    return Panel(out, box=box.ROUNDED, border_style="grey27", padding=(0, 1))


def render_header_revamp(app, width: int) -> Panel:
    """New compact animated header: living equalizer logo + wave wordmark."""
    theme, t = app.theme, app.t()
    out = Text()
    eq = "▁▂▃▄▅▆▇█"
    bar_count = 14
    for i in range(bar_count):
        v = abs(math.sin(t * 2.6 + i * 0.75)) * 0.7 + abs(math.sin(t * 3.3 - i * 0.45)) * 0.3
        idx = min(7, int(v * 8))
        out.append(eq[idx], style=theme_color(theme, t, phase=i * 0.35,
                                              light=0.5 + 0.35 * v, sat=0.9))
    out.append("  ", style="")
    for i in range(3):
        out.append("♥", style=theme_color(theme, t, phase=i * 0.9 + t * 2.5, light=0.75))
    out.append("\n")
    word = "T E R M I F Y"
    for i, c in enumerate(word):
        w = 0.5 + 0.5 * math.sin(t * 2.0 + i * 0.55)
        out.append(c, style=f"bold {theme_color(theme, t, phase=i * 0.5, light=0.62 + 0.28 * w, sat=0.95)}")
    out.append("\n")
    from rich.columns import Columns
    right = Text()
    right.append("  ♪ " + app.engine.me_name + "\n", style="bold white")
    right.append("  ", style="")
    for i, c in enumerate(theme):
        right.append(c, style=theme_color(theme, t, phase=i * 0.6, light=0.7))
    right.append("\n", style="")
    right.append("  " + TAGLINE + "\n", style="grey40")
    right.append("  by ", style="grey40")
    right.append("@johnthemailboy", style=f"bold {theme_color(theme, t, phase=1.7)}")
    content = Columns([out, right], expand=True, padding=(0, 2))
    return Panel(content, box=box.ROUNDED, border_style=panel_border(theme, t),
                 padding=(0, 1))


TAB_ITEMS = [
    ("home", "🏠", "Home"),
    ("search", "🔍", "Search"),
    ("playlists", "📁", "Playlists"),
    ("liked", "♥", "Liked"),
    ("library", "📊", "Library"),
    ("devices", "📡", "Devices"),
    ("queue", "🎵", "Queue"),
    ("lyrics", "🎤", "Lyrics"),
    ("settings", "⚙", "Settings"),
]


def render_tabbar(app, width: int, x0: int, y0: int) -> Panel:
    """Navigation as an animated tab bar (revamp layout)."""
    theme, t = app.theme, app.t()
    active = {
        "playlist_tracks": "playlists",
        "artist": "search",
        "album": "search",
    }.get(app.view, app.view)
    out = Text()
    n = len(TAB_ITEMS)
    inner = width - 4
    per = max(8, inner // n)
    sel = 0
    for idx, (key, icon, label) in enumerate(TAB_ITEMS):
        is_active = active == key
        cell = icon + " " + label
        cell = truncate(cell, per - 2)
        app.add_zone(x0 + 1 + idx * per, y0, per, 1, type="nav", view=key)
        if is_active:
            sel = idx
            accent = sel_accent(theme, t)
            out.append(" " + cell.ljust(per - 2) + " ",
                       style=f"bold black on {accent}")
        else:
            pulse = 0.5 + 0.2 * math.sin(t * 3 + idx * 1.3)
            out.append(" " + cell.ljust(per - 2) + " ",
                       style=theme_color(theme, t, phase=idx * 0.8, light=pulse))
    out.append("\n")
    pos = sel * per + 1
    underline = " " * pos + "▲" + " " * (inner - pos - 1)
    for i, c in enumerate(underline):
        if c == "▲":
            out.append("▲", style=theme_color(theme, t, light=0.8))
        else:
            out.append(c, style="grey23")
    return Panel(out, box=box.ROUNDED, border_style=panel_border(theme, t),
                 padding=(0, 1))


def render_nav_revamp(app, x0: int, y0: int, height: int) -> Panel:
    """Left sidebar = your playlists (revamp layout)."""
    theme, t = app.theme, app.t()
    out = Text()
    out.append(" PLAYLISTS\n", style=f"bold {theme_color(theme, t, light=0.6)}")
    out.append("─" * 20 + "\n", style="grey27")
    rows = app.rows.get("playlists", [])
    if app.loading.get("playlists"):
        out.append(" loading…\n", style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    elif not rows:
        out.append(" (none yet)\n", style="grey35")
    avail = max(2, height - 9)
    sel_pl = max(0, app.sel["playlists"] - 1)
    sc = app.scroll["playlists"]
    if sel_pl < sc:
        sc = sel_pl
    if sel_pl >= sc + avail:
        sc = sel_pl - avail + 1
    sc = max(0, min(sc, max(0, len(rows) - avail)))
    app.scroll["playlists"] = sc
    accent = sel_accent(theme, t)
    app.add_zone(x0 + 1, y0 + 2, 20, 1, type="sidebar", index=0)
    if app.sel["playlists"] == 0:
        out.append(" ❯ ♥ Liked Songs\n", style=f"bold black on {accent}")
    else:
        out.append("   ♥ Liked Songs\n", style="grey70")
    for i in range(sc, min(len(rows), sc + avail)):
        pl = rows[i]
        view_idx = i + 1
        app.add_zone(x0 + 1, y0 + 3 + (i - sc), 20, 1,
                     type="sidebar", index=view_idx)
        sel = app.sel["playlists"] == view_idx
        label = truncate(pl.name, 18)
        if sel:
            out.append(f" ❯ {label.ljust(18)}\n", style=f"bold black on {accent}")
        else:
            out.append(f"   {label.ljust(18)}\n", style="grey70")
    if len(rows) > sc + avail:
        out.append(f"   …{len(rows) - sc - avail} more\n", style="grey35")
    out.append("\n")
    dev = truncate(app.snap.device_label, 18)
    if dev:
        out.append("♪ " + dev + "\n", style=theme_color(theme, t, light=0.5))
    out.append("[enter] open · [a] play\n", style="grey35")
    return Panel(out, box=box.ROUNDED, border_style=panel_border(theme, t),
                 padding=(0, 1))


def status_pip(app) -> Text:
    snap = app.snap
    theme, t = app.theme, app.t()
    out = Text()
    if snap.status == "buffering":
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        f = frames[int(t * 10) % len(frames)]
        out.append(f" {f} buffering… ", style=theme_color(theme, t, light=0.6))
    elif snap.playing:
        out.append(" ▶ playing ", style=theme_color(theme, t, light=0.55))
    elif snap.status == "paused":
        out.append(" ❚❚ paused ", style="grey62")
    elif snap.status == "error":
        out.append(" ⚠ error ", style="bold #ff5555")
    else:
        out.append(" ◼ idle ", style="grey50")
    if getattr(app, "sleep_end", None):
        left = max(0, int((app.sleep_end - _time.monotonic()) / 60))
        out.append(f" 😴{left}m", style="grey62")
    return out


def render_home(app, width: int, height: int, x0: int, y0: int) -> Panel:
    from rich.columns import Columns
    from rich.console import Group

    theme, t = app.theme, app.t()
    snap: Snapshot = app.snap
    inner_w = width - 4
    inner_h = height - 2

    # bigger art = higher visible resolution; cap generous when there's room
    art_w = max(16, min(40, (inner_w * 3) // 5))
    if inner_w - art_w - 2 < 18:
        art_w = max(12, inner_w - 20)
    art_h = max(9, min(art_w // 2, inner_h - 10))
    info_w = max(14, inner_w - art_w - 2)

    track = snap.track
    art_img = app.art_for(track.image_url if track else None, art_w, art_h)

    info = Text()
    info.append("\n")
    if track:
        info.append(marquee(track.name, max(8, info_w - 2), t) + "\n",
                    style=f"bold {theme_color(theme, t, light=0.70)}")
        info.append(truncate(track.artists, info_w - 2) + "\n", style="white")
        info.append(truncate(track.album, info_w - 2) + "\n", style="grey58")
        info.append("\n")
        if track.liked:
            info.append(" ♥ liked ", style=theme_color(theme, t, phase=0.8))
            info.append("   ", style="")
        info.append("↻ " + {"off": "off", "context": "all", "track": "one"}[snap.repeat],
                    style=theme_color(theme, t, light=0.5) if snap.repeat != "off" else "grey37")
        info.append("   ⇄ " + ("on" if snap.shuffle else "off"),
                    style=theme_color(theme, t, light=0.5) if snap.shuffle else "grey37")
        info.append("\n\n")
        if snap.context_name:
            info.append(" from ", style="grey42")
            info.append(truncate(snap.context_name, info_w - 8), style="grey62")
    else:
        info.append(" nothing playing\n", style="grey58")
        info.append("\n browse your playlists or search,\n", style="grey42")
        info.append(" then hit enter on any track.\n", style="grey42")

    top_cols = Columns([art_img, info], expand=False, padding=(0, 2))

    # the panel content starts with the taller of (art, info); progress after it
    _plain = info.plain
    info_h = _plain.count("\n") + (0 if _plain.endswith("\n") else 1)
    top_h = max(art_h, info_h)

    progress_ratio = (snap.position_ms / snap.duration_ms) if snap.duration_ms else 0.0
    prog = bar(inner_w, progress_ratio, theme, t)
    prog_row = top_h + 1
    # cover the bar row AND the timing row below it, so clicking the visible
    # "click bar to seek" prompt works (not just the thin bar itself).
    app.add_zone(x0, y0 + prog_row, inner_w, 2, type="seek")
    timing = Text()
    pre = f" {snap.position_text} "
    post = f"{snap.duration_text} "
    hint = "click bar to seek"
    gap = max(1, inner_w - len(pre) - len(hint) - 3 - len(post))
    timing.append(pre, style="grey70")
    timing.append(" " * gap, style="")
    timing.append(hint, style="grey30")
    timing.append("   ", style="")
    timing.append(post, style="grey50")

    # remaining vertical space after art + progress block (blank, prog, timing, blank)
    remaining = max(0, inner_h - top_h - 4)
    viz_rows = max(0, min(7, remaining - 2))
    q_rows = max(0, remaining - viz_rows - 1)
    if q_rows < 2 and viz_rows > 2:
        viz_rows -= 2 - q_rows
        q_rows = max(0, remaining - viz_rows - 1)

    viz = visualizer(track.id if track else "idle", inner_w - 2, max(2, viz_rows),
                     t, snap.playing, theme,
                     bands=getattr(app, "live_bands", None))

    q_header_row = prog_row + 3 + max(2, viz_rows)
    q = Text()
    sel_home = min(app.sel["home"], max(0, len(snap.queue) - 1))
    app.sel["home"] = sel_home
    q.append(" UP NEXT  ", style="bold grey50")
    q.append("[enter] jump\n", style="grey37")
    if snap.queue and q_rows > 0:
        for i, tr in enumerate(snap.queue[:q_rows]):
            app.add_zone(x0, y0 + q_header_row + 1 + i, inner_w, 1,
                         type="queue", index=i)
            line = f" {i + 1:>2} {tr.name} — {tr.artists}"
            line = truncate(line, inner_w - 3)
            if i == sel_home:
                accent = theme_color(theme, t, light=0.55)
                q.append("❯ " + line.ljust(inner_w - 3) + "\n",
                         style=f"bold black on {accent}")
            else:
                q.append("  " + line + "\n",
                         style="grey62" if i else theme_color(theme, t, phase=0.4))
    else:
        q.append(" (queue empty)\n", style="grey35")

    body = Group(
        top_cols,
        Text(""),
        prog,
        timing,
        Text(""),
        viz,
        q,
    )
    return Panel(body, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def list_title(title: str, count: int, hint: str, theme: str, t: float) -> Text:
    out = Text()
    out.append(f" {title} ", style=f"bold {theme_color(theme, t, light=0.6)}")
    out.append(f" ({count})  ", style="grey50")
    out.append(truncate(hint, 40), style=theme_color(theme, t, phase=1.0, light=0.45))
    return out


def render_track_list(app, kind: str, title: str,
                      tracks: List[Track], width: int, height: int,
                      x0: int, y0: int) -> Panel:
    theme, t = app.theme, app.t()
    rows_avail = max(3, height - 5)
    scroll = window(app, kind, rows_avail, len(tracks))
    sel = app.sel[kind]
    sort = app.sort_label(kind)
    hint = f" [enter] play   [o] sort: {sort if sort else '—'}   [x] reload "
    out = Text()
    out.append_text(list_title(title, len(tracks), hint, theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if app.loading.get(kind):
        out.append(" loading…\n", style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    elif not tracks:
        out.append(" (empty)\n", style="grey42")
    by_date = app.sort_label(kind) in ("oldest added", "newest added")
    for i in range(scroll, min(len(tracks), scroll + rows_avail)):
        app.add_zone(x0, y0 + 2 + (i - scroll), width - 2, 1,
                     type="select", view=kind, index=i)
        out.append_text(
            track_row(tracks[i], i, i == sel, width - 4, theme, t, by_date)
        )
        out.append("\n")
    return Panel(out, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def render_queue(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """The full line-up: what's spinning now + every song waiting its turn."""
    theme, t = app.theme, app.t()
    snap: Snapshot = app.snap
    q = snap.queue
    can_edit = callable(getattr(app.engine, "queue_remove", None))
    hint = " [enter] jump to it · [d] kick out · [x] reload " if can_edit \
        else " your up-next line "
    out = Text()
    out.append_text(list_title("QUEUE ♫", len(q), hint, theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")

    tr = snap.track
    out.append(" NOW PLAYING\n", style="bold grey50")
    if tr:
        pip = "▶" if snap.playing else "❚❚"
        name = f" {pip}  {tr.name} — {tr.artists}"
        tail = f"{snap.position_text}/{tr.duration_text}"
        room = max(8, width - 6 - len(tail))
        line = Text()
        line.append_text(gradient_text(truncate(name, room).ljust(room),
                                       theme, t, step=0.14))
        line.append(" ")
        line.append(tail, style="grey50")
        out.append_text(line)
        out.append("\n")
    else:
        out.append(" nothing playing right now\n", style="grey50")
    out.append("\n")
    out.append(f" UP NEXT ({len(q)})\n", style="bold grey50")

    before = 7  # title + divider + now-hdr + now-row + blank + upnext-hdr
    rows_avail = max(2, height - 2 - before)
    scroll = window(app, "queue", rows_avail, len(q))
    sel = app.sel["queue"]
    if not q:
        msg = (" (the line is empty - start something from playlists/search "
               "and it builds up here)\n" if tr else " (queue empty)\n")
        out.append(msg, style="grey35")
    for i in range(scroll, min(len(q), scroll + rows_avail)):
        line_y = y0 + out.plain.count("\n")
        app.add_zone(x0, line_y, width - 2, 1, type="queue", index=i)
        out.append_text(track_row(q[i], i, i == sel, width - 4, theme, t))
        out.append("\n")
    if len(q) > scroll + rows_avail:
        out.append(f"   … {len(q) - scroll - rows_avail} more below "
                   "(scroll / PgDn)\n", style="grey35")
    return Panel(out, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40))


def _thumb_colors(name: str) -> Tuple[str, str]:
    """Two deterministic colors per playlist, standing in for cover art."""
    code = sum((i + 1) * ord(c) for i, c in enumerate(name))
    hue = code % 360
    r1, g1, b1 = colorsys.hls_to_rgb(hue / 360.0, 0.58, 0.78)
    r2, g2, b2 = colorsys.hls_to_rgb(((hue + 30) % 360) / 360.0, 0.36, 0.75)
    to_hex = lambda c: f"#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}"
    return to_hex((r1, g1, b1)), to_hex((r2, g2, b2))


def playlist_card(name: str, owner: str, count: int, idx: int,
                  selected: bool, width: int, theme: str, t: float,
                  pinned: bool = False) -> Tuple[Text, Text]:
    """A 2-line playlist row: mini cover on the left, title + who/counts."""
    top, low = _thumb_colors("liked songs" if pinned else name)
    caret = "❯" if selected else " "
    num = f"{idx:>3} " if not pinned else "    "
    meta = f"{owner} · {count} tracks"
    a = Text()
    b = Text()
    a.append(caret, style=f"bold {theme_color(theme, t, light=0.6)}"
              if selected else "grey30")
    b.append(" ", style="")
    a.append("██" if not pinned else "♥♥", style=top)
    b.append("██" if not pinned else "╚╝", style=low)
    a.append(" ")
    name_w = max(8, width - 4 - 1 - 2 - 1 - 4)
    if selected:
        accent = theme_color(theme, t, light=0.55)
        a.append(num, style=f"bold black on {accent}")
        a.append(truncate(name, name_w).ljust(name_w),
                 style=f"bold black on {accent}")
    else:
        a.append(num, style="grey45")
        a.append(truncate(name, name_w).ljust(name_w), style="bold white")
    b.append("   ")
    b.append(truncate(meta, max(8, width - 12)), style="grey50")
    return a, b


def render_playlists(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """Playlists as full-width rows: cover thumb + name + meta. Each row is
    one predictable, fully-clickable zone (no Columns misalignment)."""
    theme, t = app.theme, app.t()
    rows = app.rows.get("playlists", [])
    total = len(rows) + 1  # include pinned Liked Songs
    sel = app.sel["playlists"]
    inner = max(20, width - 4)
    thumb_w = 10
    cover_h = 4
    row_h = cover_h + 1   # cover rows + one meta line

    out = Text()
    out.append_text(list_title(
        "PLAYLISTS", total,
        f"· {sel + 1}/{total} · [enter] open · [a] play ", theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if app.loading.get("playlists"):
        out.append(" loading…\n",
                   style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
        return Panel(out, box=box.ROUNDED, border_style=panel_border(theme, t))

    def cover_block(name, img_url):
        art = app.art_for(img_url, thumb_w, cover_h)
        if art is None:
            top, low = _thumb_colors(name)
            art = Text()
            for r in range(cover_h):
                art.append(("▄" * thumb_w) if r < cover_h // 2
                           else ("▀" * thumb_w),
                           style=top if r < cover_h // 2 else low)
                art.append("\n")
        return art

    avail = max(1, (height - 8) // row_h)

    def add_row(view_idx, name, meta, img_url, screen_row, is_liked=False):
        is_sel = (sel == view_idx)
        accent = sel_accent(theme, t)
        # clickable zone covering this full row
        row_y = y0 + 2 + screen_row * row_h
        app.add_zone(x0 + 1, row_y, inner, row_h,
                     type="select", view="playlists", index=view_idx)
        out.append("❯" if is_sel else " ", style="bold" if is_sel else "grey30")
        art = cover_block(name, img_url)
        art_lines = art.plain.split("\n")[:cover_h]
        sel_style = f"bold black on {accent}" if is_sel else ""
        for r in range(cover_h):
            line = art_lines[r] if r < len(art_lines) else " " * thumb_w
            if r == 0:
                out.append(" ", style="")
                out.append(line.ljust(thumb_w),
                           style="grey60" if not is_sel else sel_style)
                name_txt = "♥ " + name if is_liked else name
                out.append("  ", style="")
                out.append(truncate(name_txt, max(8, inner - thumb_w - 12)),
                           style="bold white" if not is_sel else sel_style)
                out.append("\n")
            else:
                out.append(" ", style="")
                out.append(line.ljust(thumb_w),
                           style="grey60" if not is_sel else sel_style)
                out.append("\n")
        out.append(" " + " " * thumb_w + "  ", style="")
        out.append(meta, style="grey50" if not is_sel else f"black on {accent}")
        out.append("\n")

    # scroll window: only render 'avail' rows around the selection
    sc = window(app, "playlists", avail, total)
    first = max(0, sc)  # index of first playlist to show (0 = Liked)
    for v_idx in range(first, min(total, first + avail)):
        if v_idx == 0:
            add_row(0, "Liked Songs", "your collection · ∞ tracks",
                    "demo:liked", v_idx - first, is_liked=True)
        else:
            pl = rows[v_idx - 1]
            add_row(v_idx, pl.name,
                    f"by {pl.owner or 'spotify'} · {pl.count} tracks",
                    pl.image_url or f"demo:pl_{pl.name}", v_idx - first)
    if total > first + avail:
        out.append(f"   … {total - first - avail} more below (wheel / PgDn)\n",
                   style="grey35")
    return Panel(out, box=box.ROUNDED, border_style=panel_border(theme, t))


def render_devices(app, width: int, height: int, x0: int, y0: int) -> Panel:
    theme, t = app.theme, app.t()
    out = Text()
    devs = app.rows.get("devices", [])
    out.append_text(list_title("DEVICES", len(devs),
                               " [enter] use device   [x] rescan ", theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if app.engine.mode == "stream":
        out.append("\n the embedded player is active —\n", style="grey62")
        out.append(" audio comes straight from this terminal.\n", style="grey42")
        out.append("\n ♪ " + app.engine.device_label + "\n",
                   style=theme_color(theme, t, light=0.55))
    elif app.loading.get("devices"):
        out.append(" scanning…\n", style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    else:
        if not devs:
            out.append("\n no devices seen by Spotify yet.\n", style="grey62")
            out.append(" open the spotify app / open.spotify.com\n", style="grey42")
            out.append(" once on any device, then press x.\n", style="grey42")
        sel = app.sel["devices"]
        active_id = getattr(app.engine, "_device_id", None)
        for i, d in enumerate(devs[: max(3, height - 6)]):
            app.add_zone(x0, y0 + 2 + i, width - 2, 1,
                         type="select", view="devices", index=i)
            out.append_text(
                device_row(d, i, i == sel, d.get("id") == active_id, width - 4, theme, t)
            )
            out.append("\n")

    if app.snap.track:
        out.append("\n lyrics for this track live in their own view\n", style="grey42")
        out.append(" press L or [8] to open the lyrics panel 🎤\n", style="grey37")
    return Panel(out, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def render_settings(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """Settings: switch layout, see info. Pressing the row toggles it."""
    theme, t = app.theme, app.t()
    out = Text()
    out.append_text(list_title("SETTINGS", 1, " [enter] toggle · click a row ", theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")

    # ---- layout toggle row ----
    app.add_zone(x0, y0 + 2, width - 2, 1, type="btn", action="layout")
    cur = "REVAMP (tab bar + playlist sidebar)" if app.layout == "revamp" else "CLASSIC (original)"
    row = Text()
    row.append(" ❯ ", style=theme_color(theme, t, light=0.6))
    row.append("Layout:  ", style="bold white")
    row.append(cur, style=theme_color(theme, t, light=0.6))
    row.append("\n", style="")
    row.append("    (switch between the two interfaces)  [enter]\n", style="grey45")
    out.append_text(row)
    out.append("\n", style="")

    # ---- theme hint row ----
    app.add_zone(x0, y0 + 5, width - 2, 1, type="btn", action="theme")
    row2 = Text()
    row2.append(" ❯ ", style=theme_color(theme, t, light=0.6))
    row2.append("Theme:  ", style="bold white")
    for i, ch in enumerate(app.theme):
        row2.append(ch, style=theme_color(theme, t, phase=i * 0.6, light=0.7))
    row2.append("\n", style="")
    row2.append("    (cycle the 15 color themes)  [t]\n", style="grey45")
    out.append_text(row2)

    out.append("\n", style="")
    out.append(" made with ♥ by @johnthemailboy\n", style="grey40")
    out.append(" termify is an unofficial, personal-use client.\n", style="grey35")
    return Panel(out, box=box.ROUNDED, border_style=panel_border(theme, t))


def render_search(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """Rich search results: artists / albums / playlists / tracks sections."""
    theme, t = app.theme, app.t()
    rows = app.rows.get("search", [])
    rows_avail = max(3, height - 5)
    scroll = window(app, "search", rows_avail, len(rows))
    sel = app.sel["search"]
    flat = [r for r in rows if r[0] != "section"]
    out = Text()
    out.append_text(list_title(
        f"SEARCH /{app.search_q}" if app.search_q else "SEARCH",
        len(flat), " [/] new search   [enter] open/play ", theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if app.loading.get("search"):
        out.append(" searching spotify…\n",
                   style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    elif not rows and app.search_q:
        out.append(f" no results for '{app.search_q}'\n", style="grey50")
        out.append(" press / to try another search\n", style="grey37")
    elif not rows:
        out.append(" press / and type something - a song, artist, album…\n",
                   style="grey50")
    for i in range(scroll, min(len(rows), scroll + rows_avail)):
        kind, obj = rows[i]
        if kind == "section":
            out.append("\n ", style="")
            out.append(f" {obj} ", style=f"bold {theme_color(theme, t, light=0.62)}")
            out.append("\n", style="")
            continue
        selected = i == sel
        line_y = y0 + out.plain.count("\n")
        app.add_zone(x0, line_y, width - 2, 1,
                     type="select", view="search", index=i)
        if kind == "track":
            out.append_text(track_row(obj, i - scroll, selected, width - 4, theme, t))
        else:
            if kind == "artist":
                badge, name, meta = "ARTIST", obj.name, "tap into their top tracks"
            elif kind == "album":
                badge, name, meta = "ALBUM ", obj.name, (
                    f"{obj.artists}" + (f" · {obj.year}" if obj.year else "")
                )
            else:  # playlist
                badge, name, meta = "PLAYLIST", obj.name, (
                    f"by {obj.owner} · {obj.count} tracks"
                )
            caret = "❯" if selected else " "
            if selected:
                accent = theme_color(theme, t, light=0.55)
                body = f"  [{badge}]  {truncate(name, max(10, width - 30))}  {truncate(meta, 28)}"
                out.append(f"{caret} ", style=f"bold black on {accent}")
                out.append(body.ljust(width - 4), style=f"bold black on {accent}")
            else:
                out.append(f"{caret} ", style="grey30")
                out.append(f"  [{badge}]  ", style=theme_color(theme, t, phase=i * 0.4, light=0.5))
                out.append(truncate(name, max(10, width - 30)), style="white")
                out.append("  " + truncate(meta, 28), style="grey50")
        out.append("\n")
    return Panel(out, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def render_lyrics(app, width: int, height: int) -> Panel:
    """Karaoke panel: synced lyrics follow the playback position."""
    theme, t = app.theme, app.t()
    st = app.lyrics_state
    snap = app.snap
    tr = snap.track
    out = Text()
    src = st.get("source", "")
    if st.get("synced"):
        note = "synced via lrclib.net ✓ karaoke"
    elif src == "genius":
        note = "via genius.com · plain text (no timestamps for this one)"
    elif src == "lrclib":
        note = "via lrclib.net · plain text"
    else:
        note = "lrclib.net + genius.com"
    out.append_text(gradient_text(" LYRICS ", theme, t, step=0.4))
    out.append(f"   [L / esc] back · {note}", style="grey37")
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if tr:
        out.append(f" ♪ {tr.name} — {tr.artists}\n\n", style="grey62")
    if st.get("loading"):
        out.append(" looking up lyrics…\n",
                   style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    elif st.get("synced"):
        synced = st["synced"]
        cur = lyric_index(synced, snap.position_ms)
        lo = max(0, min(cur - 3, len(synced) - 8))
        hi = min(len(synced), lo + 9)
        for i in range(lo, hi):
            _ms, line = synced[i]
            if i == cur:
                out.append(" ❯ ", style=theme_color(theme, t, light=0.7))
                out.append_text(gradient_text(line, theme, t, step=0.10))
                out.append("\n")
            else:
                style = "grey42" if i < cur else "grey58"
                out.append(f"   {line}\n", style=style)
    elif st.get("plain"):
        out.append(" (found lyrics, but no timestamps for this one)\n\n", style="grey42")
        for line in st["plain"][: max(6, height - 8)]:
            out.append(f"   {line}\n", style="grey62")
    else:
        out.append(" no lyrics found for this track ♪\n", style="grey50")
        out.append(" tip: synced tracks light up karaoke-style as they play\n",
                   style="grey35")
    return Panel(out, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40))


def render_picker(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """'Add to playlist' chooser."""
    theme, t = app.theme, app.t()
    tr = app.picker["track"]
    rows = app.rows.get("playlists", [])
    sel = app.picker["sel"]
    out = Text()
    out.append_text(gradient_text(" ADD TO PLAYLIST ", theme, t, step=0.4))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    out.append(f" track: {tr.name} — {tr.artists}\n\n", style="grey62")
    avail = max(3, height - 8)
    first = max(0, min(sel - avail // 2, max(0, len(rows) - avail)))
    for i in range(first, min(len(rows), first + avail)):
        pl = rows[i]
        app.add_zone(x0 + 1, y0 + 6 + i - first, width - 4, 1,
                     type="picker", index=i)
        if i == sel:
            accent = theme_color(theme, t, light=0.55)
            out.append(f" ❯ {truncate(pl.name, width - 8)}".ljust(width - 4) + "\n",
                       style=f"bold black on {accent}")
        else:
            out.append(f"   {truncate(pl.name, width - 16)}", style="grey70")
            out.append(f"  {pl.count}", style="grey37")
            out.append("\n")
    if not rows:
        out.append(" loading your playlists…\n", style="grey50")
    out.append("\n [enter] add   [esc/q] cancel   (double-click adds · right-click any track opens this)\n",
               style="grey40")
    return Panel(out, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40))


def render_library(app, width: int, height: int, x0: int, y0: int) -> Panel:
    """Stats & history: recently played, top tracks, top artists."""
    theme, t = app.theme, app.t()
    rows = app.rows.get("library", [])
    rows_avail = max(3, height - 5)
    scroll = window(app, "library", rows_avail, len(rows))
    sel = app.sel["library"]
    flat = [r for r in rows if r[0] != "section"]
    out = Text()
    out.append_text(list_title(
        "LIBRARY · STATS", len(flat),
        " [enter] open/play · [x] reload · [A] add to playlist ", theme, t))
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")
    if app.loading.get("library"):
        out.append(" crunching your listening stats…\n",
                   style=theme_color(theme, t, light=0.55 + 0.2 * math.sin(t * 5)))
    for i in range(scroll, min(len(rows), scroll + rows_avail)):
        kind, obj = rows[i]
        if kind == "section":
            out.append("\n ", style="")
            out.append(f" {obj} ", style=f"bold {theme_color(theme, t, light=0.62)}")
            out.append("\n", style="")
            continue
        selected = i == sel
        line_y = y0 + out.plain.count("\n")
        app.add_zone(x0, line_y, width - 2, 1,
                     type="select", view="library", index=i)
        if kind == "track":
            out.append_text(track_row(obj, i - scroll, selected, width - 4, theme, t))
        else:  # artist
            caret = "❯" if selected else " "
            if selected:
                accent = theme_color(theme, t, light=0.55)
                body = (f"  [ARTIST]  {truncate(obj.name, max(10, width - 30))}"
                        f"  tap into their top tracks")
                out.append(f"{caret} ", style=f"bold black on {accent}")
                out.append(body.ljust(width - 4), style=f"bold black on {accent}")
            else:
                out.append(f"{caret} ", style="grey30")
                out.append("  [ARTIST]  ",
                           style=theme_color(theme, t, phase=i * 0.4, light=0.5))
                out.append(truncate(obj.name, max(10, width - 30)), style="white")
                out.append("  tap into their top tracks", style="grey50")
        out.append("\n")
    return Panel(out, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def render_stats(app, width: int, height: int) -> Panel:
    """'S' overlay: your listening stats + a 'your week in music' digest."""
    theme, t = app.theme, app.t()
    st = app.stats
    out = Text()
    out.append_text(gradient_text(" LISTENING STATS ", theme, t, step=0.4))
    out.append("   [S / esc] close", style="grey37")
    out.append("\n" + "─" * (width - 4) + "\n", style="grey27")

    def row(label: str, value: str, style: str = "") -> None:
        out.append(f"  {label:<13}", style=f"bold {theme_color(theme, t, light=0.6)}")
        out.append(value + "\n", style=style or "white")

    row("today", fmt_ms(st.ms_today()), theme_color(theme, t, light=0.7))
    row("last 7 days", fmt_ms(st.ms_period(7)))
    row("all time", fmt_ms(st.ms_all()), "grey62")
    day_streak = st.streak_days()
    row("day streak", f"{day_streak} day{'s' if day_streak != 1 else ''} 🔥"
        if day_streak else "0", theme_color(theme, t, light=0.6))
    row("since", st.data.get("since", "") or "—", "grey50")

    out.append("\n " + "─" * (width - 6) + "\n", style="grey27")
    out.append(" 📅  YOUR WEEK IN MUSIC\n", style=f"bold {theme_color(theme, t, light=0.6)}")
    rep = st.weekly_report()
    row("minutes", f"{rep['minutes']} min")
    row("streak", f"{rep['streak']} day{'s' if rep['streak'] != 1 else ''}",
        "grey62" if rep["streak"] else "grey40")
    out.append("  top tracks:\n", style="grey58")
    if rep["top_tracks"]:
        for i, (name, artists, ms) in enumerate(rep["top_tracks"], 1):
            out.append(f"   {i}. {truncate(name, max(8, width - 40))}"
                       f" — {truncate(artists, 22)}", style="white")
            out.append(f"  ({fmt_ms(ms)})\n", style="grey45")
    else:
        out.append("   nothing yet - go listen! ♪\n", style="grey42")
    out.append("  top artists:\n", style="grey58")
    if rep["top_artists"]:
        for i, (artist, ms) in enumerate(rep["top_artists"], 1):
            out.append(f"   {i}. {truncate(artist, max(8, width - 30))}"
                       f"  ({fmt_ms(ms)})\n", style="white")
    else:
        out.append("   nothing yet\n", style="grey42")
    out.append("\n  stats live on your machine in ~/.termify/stats.json\n",
               style="grey35")
    out.append("  (nothing is sent anywhere - it's yours) ✓\n", style="grey35")
    return Panel(out, box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40))


HELP_LINES = [
    ("views",   "1…7 / tab / ↑↓ j/k + enter  (or click them)"),
    ("mouse",   "click seek bar to scrub · click volume · click rows/nav · wheel scrolls · right-click a track = add to playlist"),
    ("play",    "space = pause/resume · n next · b prev · ←/→ seek 5 s · ,/. seek 30 s"),
    ("volume",  "+ / − (5 % steps) · click/drag the footer bar"),
    ("modes",   "s shuffle · r repeat off→all→one"),
    ("like",    "l = like/unlike current track"),
    ("lyrics",  "L or [8] = full lyrics view (lrclib sync; genius.com text fallback)"),
    ("library", "5 = recently played + your top tracks & top artists"),
    ("search",  "/ type — returns artists, albums, playlists & tracks"),
    ("sort",    "o cycles: default → oldest added → newest added → title → artist → album → duration"),
    ("playlist", "enter opens · 'a' plays whole thing · 'x' reloads · [ = sidebar playlist drawer (stays on Home)"),
    ("edit",    "C create playlist · A add track to playlist · d remove from open one · F find duplicates"),
    ("queue",   "u or 7 = full queue view · enter/click jumps · d kicks out · N = play next · E = queue at end"),
    ("sleep",   "Z cycles the sleep timer 15→30→45→60 min→off (pauses for you)"),
    ("resume",  "R resumes your last session where you left it (saved on quit)"),
    ("stats",   "S = listening stats + 'your week in music' report (stored locally)"),
    ("devices", "m opens devices · enter picks one (remote mode)"),
    ("look",    "t cycles 15 themes (aurora/sunset/ocean/candy/vampire 🦇/mono/chroma/rainbow/neon/synthwave/toxic/inferno/ice/gold/plasma)"),
    ("layout",  "] toggles the layout: revamp (tab bar + playlist sidebar) ↔ classic (original nav)"),
]


def render_help(app, width: int, height: int) -> Panel:
    theme, t = app.theme, app.t()
    out = Text()
    out.append_text(gradient_text(" KEYBOARD MAP ", theme, t, step=0.4))
    out.append("\n")
    out.append(" " + "─" * (width - 8) + "\n\n", style="grey27")
    for row in HELP_LINES:
        name, keys = row[0], row[1]
        extra = row[2] if len(row) > 2 else ""
        out.append(f"  {name:<9}", style=f"bold {theme_color(theme, t, light=0.6)}")
        out.append(f"{keys}\n", style="grey70")
        if extra:
            out.append(f"{'':13}{extra}\n", style="grey50")
    out.append("\n  termify — by @johnthemailboy · an unofficial, personal-use client.\n", style="grey42")
    out.append("  not affiliated with Spotify AB. premium required.\n", style="grey35")
    out.append("\n  press ? or esc to go back\n", style=theme_color(theme, t, light=0.5))
    return Panel(out, box=box.ROUNDED, border_style=theme_color(theme, t, light=0.40))


def render_footer(app, width: int, x0: int, y0: int) -> Panel:
    theme, t = app.theme, app.t()
    snap = app.snap
    toast = app.current_toast()
    accent = theme_color(theme, t, light=0.58)
    line1 = Text()
    if toast:
        line1.append(" ♪ ", style=theme_color(theme, t, light=0.65))
        line1.append(truncate(toast, width - 6),
                     style=f"bold {theme_color(theme, t, light=0.62)}")
    else:
        x = 1
        # ---- transport buttons (real clickable buttons, beefy size)
        line1.append(" ")
        bface = f"bold {accent}"
        binv = f"bold black on {accent}"
        edge = theme_color(theme, t, light=0.38)
        playing_txt = Text.assemble(("[ ", edge), ("❚❚", bface), (" ]", edge)) \
            if snap.playing else \
            Text.assemble(("[ ", edge), ("▶ ", binv), (" ]", edge))
        line1.append_text(playing_txt)
        line1.append(" ")
        app.add_zone(x0 + x, y0, 6, 1, type="btn", action="toggle")
        x += 7
        line1.append_text(Text.assemble(("[ ", edge), ("◄◄", bface), (" ]", edge)))
        line1.append(" ")
        app.add_zone(x0 + x, y0, 6, 1, type="btn", action="prev")
        x += 7
        line1.append_text(Text.assemble(("[ ", edge), ("►►", bface), (" ]", edge)))
        line1.append(" ")
        app.add_zone(x0 + x, y0, 6, 1, type="btn", action="next")
        x += 7
        rep_lbl = {"off": "off", "context": "all", "track": "one"}[snap.repeat]
        rep_style = bface if snap.repeat != "off" else "grey50"
        line1.append_text(Text.assemble(("[ ", edge), (f"↻{rep_lbl}", rep_style),
                                        (" ]", edge)))
        line1.append(" ")
        app.add_zone(x0 + x, y0, 8, 1, type="btn", action="repeat")
        x += 9
        sh_style = bface if snap.shuffle else "grey50"
        line1.append_text(Text.assemble(("[ ", edge), ("⇄ ", sh_style), (" ]", edge)))
        app.add_zone(x0 + x, y0, 6, 1, type="btn", action="shuffle")
        x += 7
        if getattr(app, "sleep_end", None):
            left = max(0, int((app.sleep_end - _time.monotonic()) / 60))
            chip = f" 😴{left}m"
            line1.append(chip, style="grey45")
            x += len(chip)

        # ---- the song title down here, where the eyes live
        W = width - 4               # panel border+padding eats 4 cells
        vol_w = max(6, min(14, width // 13))
        vol_block = 7 + vol_w + 5   # "   vol " + bar + " NN%"
        msg_txt = (" · " + truncate(snap.message, 14)) if snap.message else ""
        tr = snap.track
        if tr:
            raw = f"{tr.name} — {tr.artists}"
            heart_w = 2 if tr.liked else 0
            name_w = max(8, min(W - x - vol_block - heart_w
                                - len(msg_txt) - 8, 42))
            line1.append("  ♪ ", style=theme_color(theme, t, light=0.6))
            line1.append(marquee(raw, name_w, t), style="bold white")
            if tr.liked:
                line1.append(" ♥", style=theme_color(theme, t, phase=0.8, light=0.55))
            x += 4 + name_w + heart_w
        else:
            line1.append("  · nothing playing - open a list and hit enter",
                         style="grey40")
        if msg_txt:
            line1.append(msg_txt, style="grey42")
            x += len(msg_txt)
        # ---- volume bar hugs the right edge
        vol_x = W - vol_block - 1
        line1.append(" " * max(1, vol_x - x))
        line1.append("   vol ", style="grey50")
        line1.append_text(bar(vol_w, snap.volume / 100.0, theme, t))
        line1.append(f" {snap.volume:>3}%", style="grey62")
        app.add_zone(x0 + vol_x + 7, y0, vol_w, 1, type="volume")

    line2 = Text()
    if app.typing:
        target = getattr(app, "typing_target", "search")
        label = " new playlist▸ " if target == "playlist" else " search▸ "
        hint = ("  (enter to create · esc to cancel)" if target == "playlist"
                else "  (enter to search · esc to cancel)")
        line2.append(label, style=f"bold {theme_color(theme, t, light=0.6)}")
        line2.append(app.type_buf, style="white")
        line2.append("▌", style=theme_color(theme, t, light=0.6 + 0.3 * math.sin(t * 6)))
        line2.append(hint, style="grey37")
    elif getattr(app, "mouse_debug", False):
        from . import __version__
        inp = getattr(app, "input", None)
        enabled = getattr(inp, "mouse_enabled", True)
        mode = getattr(inp, "_mode", "?")
        line2.append(f" v{__version__}", style="grey46")
        if enabled:
            line2.append(f" mouse: on ({mode})", style=theme_color(theme, t, light=0.6))
        else:
            line2.append(" mouse: OFF - terminal isn't sending events"
                         f" (mode {mode})", style="bold #ff5555")
        code, x, y, hit = getattr(app, "_last_mouse", (0, 0, 0, "-"))
        age = _time.monotonic() - getattr(app, "_last_mouse_t", 0.0)
        last = f"code {code} @{x},{y}→{hit}" if age < 8 else "none yet"
        line2.append("  └ last mouse: " + last, style="grey62")
        key_age = _time.monotonic() - getattr(app, "_last_key_t", 0.0)
        key_txt = getattr(app, "_last_key", "none yet")
        shown_key = key_txt if key_age < 8 else "none yet"
        line2.append(f"   key: {shown_key}", style=theme_color(theme, t, light=0.55))
        line2.append("   [M] close", style="grey40")
    else:
        line2.append(truncate(KEY_LEGEND, width - 2), style="grey42")
    return Panel(Text.assemble(line1, "\n", line2), box=box.ROUNDED,
                 border_style=theme_color(theme, t, light=0.40), padding=(0, 1))


# ------------------------------------------------------------------ root

NAV_W = 24


def build(app, width: int, height: int):
    app.zones.clear()
    if width < 72 or height < 20:
        return Panel(
            Align.center(
                Text(f"termify needs at least 72×20\nyou have {width}×{height}\nplease resize ♪",
                     style="grey70"),
                vertical="middle",
            ),
            box=box.ROUNDED,
        )
    layout = getattr(app, "layout", "revamp")
    if layout == "classic":
        return _build_classic(app, width, height)
    return _build_revamp(app, width, height)


def _build_classic(app, width: int, height: int):
    """The original layout: big header + left NAVIGATE sidebar + footer."""
    big_logo = height >= (34 if app.theme == "vampire" else 30)
    header_h = (len(banner_for(app.theme)) + 3) if big_logo else 4
    footer_h = 4
    body_h = height - header_h - footer_h
    mx0, my0 = NAV_W + 1, header_h + 1
    fy0 = height - footer_h + 1
    root = Layout()
    root.split_column(
        Layout(name="header", size=header_h),
        Layout(name="body"),
        Layout(name="footer", size=footer_h),
    )
    root["header"].update(render_header(app, width, big_logo))
    root["footer"].update(render_footer(app, width, 2, fy0))
    main = _render_main(app, width - NAV_W, body_h, mx0, my0)
    root["body"].split_row(
        Layout(render_nav(app, 1, my0, body_h), name="nav", size=NAV_W),
        Layout(main, name="main"),
    )
    return root


def _build_revamp(app, width: int, height: int):
    """The new layout: animated header + bottom tab bar + playlist sidebar."""
    header_h = 4
    tab_h = 3
    footer_h = 5
    body_h = height - header_h - tab_h - footer_h
    # content origins MUST match where panels actually render:
    # body starts after header + tabbar (panel border + 1 content row)
    mx0 = NAV_W + 1
    my0 = header_h + tab_h + 1
    # footer is pinned to the BOTTOM of the screen, not right after the body
    fy0 = height - footer_h + 1
    root = Layout()
    root.split_column(
        Layout(name="header", size=header_h),
        Layout(name="tabbar", size=tab_h),
        Layout(name="body"),
        Layout(name="footer", size=footer_h),
    )
    root["header"].update(render_header_revamp(app, width))
    root["tabbar"].update(render_tabbar(app, width, 2, header_h + 1))
    root["footer"].update(render_footer(app, width, 2, fy0))
    main = _render_main(app, width - NAV_W, body_h, mx0, my0)
    root["body"].split_row(
        Layout(render_nav_revamp(app, 1, my0, body_h), name="nav", size=NAV_W),
        Layout(main, name="main"),
    )
    return root


def _render_main(app, main_w: int, body_h: int, mx0: int, my0: int):
    """Shared main-panel rendering, used by both layouts."""
    if app.help_visible:
        return render_help(app, main_w, body_h)
    if app.picker is not None:
        return render_picker(app, main_w, body_h, mx0, my0)
    if app.show_lyrics or app.view == "lyrics":
        return render_lyrics(app, main_w, body_h)
    if app.show_stats:
        return render_stats(app, main_w, body_h)
    if app.view == "home":
        return render_home(app, main_w, body_h, mx0, my0)
    if app.view == "search":
        return render_search(app, main_w, body_h, mx0, my0)
    if app.view == "playlists":
        return render_playlists(app, main_w, body_h, mx0, my0)
    if app.view == "playlist_tracks":
        pl = app.current_pl
        return render_track_list(
            app, "playlist_tracks",
            f"PLAYLIST ▸ {pl.name if pl else '?'}", app.rows.get("playlist_tracks", []),
            main_w, body_h, mx0, my0)
    if app.view == "queue":
        return render_queue(app, main_w, body_h, mx0, my0)
    if app.view == "liked":
        return render_track_list(app, "liked", "LIKED SONGS",
                                 app.rows.get("liked", []), main_w, body_h, mx0, my0)
    if app.view == "artist":
        ar = app.current_artist
        return render_track_list(
            app, "artist", f"ARTIST ▸ {ar.name if ar else '?'} · TRACKS",
            app.rows.get("artist", []), main_w, body_h, mx0, my0)
    if app.view == "album":
        al = app.current_album
        return render_track_list(
            app, "album", f"ALBUM ▸ {al.name if al else '?'} · {al.year if al else ''}",
            app.rows.get("album", []), main_w, body_h, mx0, my0)
    if app.view == "library":
        return render_library(app, main_w, body_h, mx0, my0)
    if app.view == "devices":
        return render_devices(app, main_w, body_h, mx0, my0)
    if app.view == "settings":
        return render_settings(app, main_w, body_h, mx0, my0)
    return Panel(Text("???"))
