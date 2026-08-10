"""Global keyboard media-button hook.

The Spotify Web API cannot stream through OS media keys on its own, so we grab
the keyboard's play/pause / next / previous keys and route them to the engine.

How it works
------------
* Windows / X11: uses the optional `keyboard` package to install a global hook,
  so the media buttons work even when the terminal isn't focused. If `keyboard`
  isn't installed (or the OS blocks it), we degrade silently - the keys then
  still work *inside* the focused terminal via the VK/sequence mapping in
  input_layer.py.

This is fully optional: if anything fails to import or start, the app runs
exactly as before (no media buttons, but no crashes either).
"""
from __future__ import annotations
import threading
from typing import Callable, Optional

# private-use markers that input_layer.py emits for media keys (kept in sync)
K_MEDIA_PLAY = "\xee\x81\x00"
K_MEDIA_NEXT = "\xee\x81\x01"
K_MEDIA_PREV = "\xee\x81\x02"
K_MEDIA_STOP = "\xee\x81\x03"


class MediaKeyController:
    """Installs a global media-key hook if possible; else does nothing."""

    def __init__(self):
        self._listener = None
        self._enabled = False
        self._kb = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self, on_event: Callable[[str], None]) -> None:
        """on_event receives 'play' | 'next' | 'prev' | 'stop'."""
        try:
            import keyboard  # optional; may be missing or blocked
        except Exception:
            return
        self._kb = keyboard
        targets = {
            "play": ["play/pause media", "media play/pause", "media play"],
            "next": ["next track", "media next"],
            "prev": ["previous track", "media previous"],
            "stop": ["stop media"],
        }
        handlers = []
        try:
            for action, names in targets.items():
                for name in names:
                    handlers.append(
                        keyboard.add_hotkey(name, lambda a=action: on_event(a))
                    )
            self._listener = handlers
            self._enabled = True
        except Exception:
            self._listener = None
            self._enabled = False

    def stop(self) -> None:
        if self._kb is not None and self._listener:
            try:
                for h in self._listener:
                    self._kb.remove_hotkey(h)
            except Exception:
                pass
        self._listener = None
        self._enabled = False
