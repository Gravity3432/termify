"""Optional real-image (Sixel) rendering for Termify.

Windows Terminal (v1.22+) supports the SIXEL graphics protocol, which lets
a program draw an ACTUAL photo into the terminal grid - no blocky ASCII.
This module is optional: if the `python-sixel-windows` package isn't
installed, or the terminal can't do sixel, we gracefully fall back to
opening the image in the OS default viewer instead.

Made with heart by @johnthemailboy.
"""
from __future__ import annotations

import io
import os
import shutil
import sys

_HAS_SIXEL = False
try:
    from python_sixel_windows import converter as _sixel_converter
    _HAS_SIXEL = True
except Exception:  # pragma: no cover
    _HAS_SIXEL = False


def sixel_available() -> bool:
    """True if the sixel library is present (terminal support is checked at
    draw time by seeing if stdout is a TTY)."""
    return _HAS_SIXEL


def image_to_sixel(img, max_w: int = 48, max_h: int = 24) -> str:
    """Convert a PIL image to a sixel escape-sequence string, scaled to fit
    roughly `max_w` terminal cells wide / `max_h` cells tall."""
    if not _HAS_SIXEL:
        return ""
    # terminal cells are roughly 2x as tall as wide in pixels; aim for the
    # largest square-ish size that fits the budget.
    from PIL import Image
    img = img.convert("RGB")
    w, h = img.size
    # target pixel dims: width ~ max_w * cell_w_px, height ~ max_h * cell_h_px
    # use cell aspect ~2 (px height = 2 * px width) for a good fit.
    target_w = max_w * 10      # ~10px per cell
    target_h = max_h * 20      # ~20px per cell
    scale = min(target_w / w, target_h / h, 1.0)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    c = _sixel_converter.SixelConverter(buf)
    out = io.StringIO()
    c.write(out)
    return out.getvalue()


def _open_in_viewer(image_path: str) -> None:
    """Open a file in the OS default viewer (works on Windows/macOS/Linux)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(image_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{image_path}"')
        else:
            os.system(f'xdg-open "{image_path}"')
    except Exception:
        pass


def show_cover(img, title: str, interactive: bool) -> bool:
    """Show a real cover image.

    Returns True if it was shown in-terminal (sixel); False if it fell back
    to opening in the OS viewer (or couldn't do anything).
    """
    if not img:
        return False
    if interactive and sixel_available():
        try:
            sixel = image_to_sixel(img)
            if sixel:
                # clear + home, enter alt screen, draw image, then a hint line
                sys.stdout.write("\x1b[?1049h")   # alt screen
                sys.stdout.write("\x1b[2J\x1b[H")  # clear
                sys.stdout.write(sixel)
                sys.stdout.write("\n\n")
                if title:
                    sys.stdout.write(f"  {title}\n")
                sys.stdout.write("  [press any key to return]\n")
                sys.stdout.flush()
                return True
        except Exception:
            pass
    # fallback: save to disk and open in the default viewer
    try:
        from . import config
        config.ensure_dirs()
        path = config.ART_CACHE / "permify_cover_view.png"
        img.convert("RGB").save(path)
        _open_in_viewer(str(path))
        return True
    except Exception:
        return False
