from __future__ import annotations

import hashlib
import io
import math
import random
import threading
from typing import Optional, Tuple

from . import config

_lock = threading.Lock()
_mem_cache: dict = {}


# ------------------------------------------------------------------ image fetch

def _disk_path(url: str):
    name = hashlib.md5(url.encode()).hexdigest() + ".png"
    return config.ART_CACHE / name


def fetch_image(url: str, size: int = 128):
    """Return a PIL Image or None. Handles https covers and demo:-seeds."""
    from PIL import Image

    with _lock:
        if url in _mem_cache:
            return _mem_cache[url]
    img = None
    if url.startswith("demo:"):
        img = procedural_cover(url, size)
    else:
        cfg_path = _disk_path(url)
        try:
            if cfg_path.exists():
                img = Image.open(cfg_path).convert("RGB")
            else:
                import requests

                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                config.ensure_dirs()
                img.save(cfg_path)
        except Exception:
            img = None
    if img is not None:
        with _lock:
            _mem_cache[url] = img
    return img


def procedural_cover(seed: str, size: int = 128):
    """Deterministic gradient cover art for demo tracks (no network)."""
    from PIL import Image, ImageDraw

    rnd = random.Random(seed)
    h1, h2 = sorted((rnd.random(), rnd.random()))
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        f = y / max(1, size - 1)
        for x in range(size):
            g = f * 0.75 + 0.25 * (x / max(1, size - 1))
            hue = (h1 + (h2 - h1) * g) % 1.0
            r, gr, b = _hsl(hue, 0.55 + 0.2 * math.sin(g * 3), 0.45 + 0.25 * g)
            px[x, y] = (int(r * 255), int(gr * 255), int(b * 255))
    draw = ImageDraw.Draw(img, "RGBA")
    for _ in range(4):
        cx, cy = rnd.randint(0, size), rnd.randint(0, size)
        rad = rnd.randint(size // 8, size // 3)
        col = (255, 255, 255, rnd.randint(18, 52))
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=col)
    # equalizer motif
    n = rnd.randint(4, 7)
    bw = size // (n * 2)
    for i in range(n):
        bh = rnd.randint(size // 6, size // 2)
        x0 = bw // 2 + i * bw * 2
        draw.rectangle([x0, size - bh, x0 + bw, size], fill=(0, 0, 0, 70))
    return img


def _hsl(h: float, s: float, l: float) -> Tuple[float, float, float]:
    import colorsys

    return colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))


# ------------------------------------------------------------------ ansi render

def cover_art_text(url: str, w_chars: int, h_rows: int):
    """Render cover art as truecolor half-block text (2 pixels per char tall)."""
    from rich.text import Text

    w_chars = max(8, w_chars)
    h_rows = max(4, h_rows)
    img = fetch_image(url)
    if img is None:
        return None
    img = img.resize((w_chars, h_rows * 2))
    px = img.load()
    text = Text()
    for y in range(0, h_rows * 2, 2):
        if y:
            text.append("\n")
        for x in range(w_chars):
            tr, tg, tb = px[x, y]
            br, bg, bb = px[x, y + 1]
            text.append("▀", style=f"rgb({tr},{tg},{tb}) on rgb({br},{bg},{bb})")
    return text


def placeholder_art(w_chars: int, h_rows: int):
    from rich.text import Text

    w_chars = max(8, w_chars)
    h_rows = max(4, h_rows)
    lines = []
    for row in range(h_rows):
        if row == 0:
            lines.append("╭" + "─" * (w_chars - 2) + "╮")
        elif row == h_rows - 1:
            lines.append("╰" + "─" * (w_chars - 2) + "╯")
        else:
            mid = row == h_rows // 2
            content = "♪".center(w_chars - 2) if mid else "░" * (w_chars - 2)
            lines.append("│" + content + "│")
    t = Text("\n".join(lines))
    t.stylize("grey35")
    return t
