from __future__ import annotations

"""Keyboard + mouse input, cross-platform.

Emits normalized events:
    ("key",   <char or readchar key sequence>)
    ("mouse", <int code>, <int x 1-based>, <int y 1-based>, <bool pressed>)

Mouse uses SGR extended reporting (\\x1b[<b;x;yM / m). If the platform/console
can't do mouse reporting, we silently fall back to keyboard-only via readchar.
"""

import sys

# mouse reporting on/off
MOUSE_ON = "\x1b[?1000h\x1b[?1002h\x1b[?1006h"
MOUSE_OFF = "\x1b[?1006l\x1b[?1002l\x1b[?1000l"

_IS_WIN = sys.platform.startswith("win")

# Canonical key codes. Every reader below (posix, windows console, readchar
# fallback) normalizes to THESE, so the rest of the app compares against a
# single platform-independent key "language". Do NOT compare keys against
# readchar.key constants elsewhere - those differ per OS ("\x1b[A" on posix
# vs "\x00H" on Windows) and that mismatch once made arrows dead on Windows.
K_ESC = "\x1b"
K_ENTER = "\r"
K_TAB = "\t"
K_SPACE = " "
K_CTRL_C = "\x03"
K_UP = "\x1b[A"
K_DOWN = "\x1b[B"
K_RIGHT = "\x1b[C"
K_LEFT = "\x1b[D"
K_PGUP = "\x1b[5~"
K_PGDN = "\x1b[6~"
K_HOME = "\x1b[H"
K_END = "\x1b[F"

# readchar (used in fallback mode) returns Windows scan-code forms such as
# "\x00H" for the up arrow; some consoles prepend "\xe0" instead of "\x00".
# Map those - plus a few odd application-mode variants - to the canonical
# VT-style sequences above.
_ALT_KEY_FORMS = {
    "\x00H": "\x1b[A", "\xe0H": "\x1b[A",
    "\x00P": "\x1b[B", "\xe0P": "\x1b[B",
    "\x00M": "\x1b[C", "\xe0M": "\x1b[C",
    "\x00K": "\x1b[D", "\xe0K": "\x1b[D",
    "\x00I": "\x1b[5~", "\xe0I": "\x1b[5~",
    "\x00Q": "\x1b[6~", "\xe0Q": "\x1b[6~",
    "\x00G": "\x1b[H", "\xe0G": "\x1b[H",
    "\x00O": "\x1b[F", "\xe0O": "\x1b[F",
    "\x1bOA": "\x1b[A", "\x1bOB": "\x1b[B",
    "\x1bOC": "\x1b[C", "\x1bOD": "\x1b[D",
    "\x1bOH": "\x1b[H", "\x1bOF": "\x1b[F",
    "\x1b[Z": "\t",
}


def normalize_key(ch: str) -> str:
    """Return the canonical form of a key, whichever platform produced it."""
    return _ALT_KEY_FORMS.get(ch, ch)

# sequences we normalize to readchar.key equivalents
_KEY_MAP = {
    "\x1b[A": "\x1b[A", "\x1bOA": "\x1b[A",   # up
    "\x1b[B": "\x1b[B", "\x1bOB": "\x1b[B",   # down
    "\x1b[C": "\x1b[C", "\x1bOC": "\x1b[C",   # right
    "\x1b[D": "\x1b[D", "\x1bOD": "\x1b[D",   # left
    "\x1b[5~": "\x1b[5~",                      # pgup
    "\x1b[6~": "\x1b[6~",                      # pgdn
    "\x1b[H": "\x1b[H", "\x1bOH": "\x1b[H",   # home
    "\x1b[F": "\x1b[F", "\x1bOF": "\x1b[F",   # end
    "\x1b[Z": "\t",                            # shift-tab -> tab
    "\x1b": "\x1b",                            # lone escape
}

_COMPLETE_FINALS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz~")


# ------------------------------------------------------------ windows console (raw records)
# ReadConsoleInputW INPUT_RECORD translation. This is THE reliable Windows
# console input path (same one prompt_toolkit uses): actual keyboard +
# MOUSE_EVENT records, no escape sequences, works in Windows Terminal AND
# classic conhost. Escaped as a pure function so tests can drive it on Linux.
VK_TO_KEY = {
    0x26: K_UP, 0x28: K_DOWN, 0x27: K_RIGHT, 0x25: K_LEFT,
    0x21: K_PGUP, 0x22: K_PGDN, 0x24: K_HOME, 0x23: K_END,
    0x0D: "\r", 0x1B: "\x1b", 0x09: "\t", 0x08: "\x08",
    0x2E: "\x7f", 0x20: " ",
}
# mouse record bits
_MBTNS = ((0x0001, 0), (0x0004, 1), (0x0002, 2))  # (bit, sgr btn): left, middle, right
_MMOVED = 0x0001
_MDOUBLE = 0x0002
_MWHEEL = 0x0004


def translate_console_record(ev: dict, prev_buttons: int):
    """Pure Windows-record -> event-tuple translation.

    `ev` keys:
      type 'key':   down bool, vk int, char str
      type 'mouse': x int, y int (0-based cells), buttons int (low word),
                    flags int, delta int (wheel HIWORD, signed)
    Returns (event-tuple or None, new_prev_buttons).
    """
    if ev.get("type") == "key":
        if not ev.get("down", True):  # ignore key-up records
            return None, prev_buttons
        vk = ev.get("vk", 0)
        if vk in VK_TO_KEY:
            return ("key", VK_TO_KEY[vk]), prev_buttons
        ch = ev.get("char") or ""
        if ch and ch < " ":  # control chars (ctrl+c etc.)
            return ("key", ch), prev_buttons
        if ch and ch.isprintable():
            return ("key", ch), prev_buttons
        return None, prev_buttons
    if ev.get("type") == "mouse":
        x, y = ev.get("x", 0), ev.get("y", 0)
        buttons = ev.get("buttons", 0) & 0xFFFF
        flags = ev.get("flags", 0)
        if flags & _MWHEEL:
            code = 64 | (1 if ev.get("delta", 0) < 0 else 0)  # 64 up / 65 down
            return ("mouse", code, max(0, x), max(0, y), False), buttons
        if flags & (_MMOVED | _MDOUBLE):
            if flags & _MDOUBLE:
                btn_code = next((c for bit, c in _MBTNS if buttons & bit), 0)
                return ("mouse", btn_code, max(0, x), max(0, y), True), buttons
            btn_code = next((c for bit, c in _MBTNS if buttons & bit), 0)
            held = bool(buttons & 0x07)  # motion w/o buttons is NOT a press
            return ("mouse", 32 | btn_code, max(0, x), max(0, y), held), buttons
        # buttons changed: emit a press on the first rising edge,
        # a release on the first falling edge.
        for bit, code in _MBTNS:
            if buttons & bit and not prev_buttons & bit:
                return ("mouse", code, max(0, x), max(0, y), True), buttons
        for bit, code in _MBTNS:
            if prev_buttons & bit and not buttons & bit:
                return ("mouse", code, max(0, x), max(0, y), False), buttons
        return None, buttons
    return None, prev_buttons



def classify(seq: str):
    """Turn a raw escape sequence into a normalized event tuple (or None).

    SGR mouse coordinates are 1-based cell numbers; we normalize to 0-based
    to match the app's layout math.
    """
    if not seq:
        return None
    if seq.startswith("\x1b[<"):
        final = seq[-1:]
        if final not in ("M", "m"):
            return None
        body = seq[3:-1]
        try:
            code_s, x_s, y_s = body.split(";")
            return ("mouse", int(code_s), max(0, int(x_s) - 1),
                    max(0, int(y_s) - 1), final == "M")
        except (ValueError, TypeError):
            return None
    if seq in _KEY_MAP:
        return ("key", _KEY_MAP[seq])
    if seq.startswith("\x1b") and len(seq) > 1:
        return None  # unknown alt-sequence; ignore rather than leak garbage
    return ("key", seq)


class InputReader:
    def __init__(self):
        self.mouse_enabled = False
        self._mode = "fallback"  # 'posix' | 'windows' | 'fallback'
        self._posix_old = None
        self._win = None

    # ------------------------------------------------------------ life cycle
    def open(self) -> None:
        try:
            if not _IS_WIN:
                import os
                import termios

                fd = sys.stdin.fileno()
                self._posix_old = termios.tcgetattr(fd)
                import tty

                tty.setraw(fd)
                self._fd = fd
                self._os = os
                self._mode = "posix"
            else:
                if self._open_windows_raw():
                    self._mode = "windows"
                elif self._open_windows_msvcrt():
                    self._mode = "windows-msvcrt"
                else:
                    self._mode = "fallback"
        except Exception:
            self._mode = "fallback"
        try:
            if self._mode in ("posix", "windows-msvcrt"):
                # raw-record mode gets mouse natively; the SGR flags are
                # for VT-style streams only.
                sys.stdout.write(MOUSE_ON)
                sys.stdout.flush()
            self.mouse_enabled = self._mode != "fallback"
        except Exception:
            pass

    def close(self) -> None:
        try:
            sys.stdout.write(MOUSE_OFF)
            sys.stdout.flush()
        except Exception:
            pass
        if self._mode == "posix" and self._posix_old is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._posix_old)
            except Exception:
                pass
        if self._mode.startswith("windows") and self._win is not None:
            try:
                k = self._win.get("k")
                if k is None:
                    import ctypes

                    k = ctypes.windll.kernel32
                k.SetConsoleMode(self._win["hIn"], self._win["in_mode"])
                k.SetConsoleMode(self._win["hOut"], self._win["out_mode"])
            except Exception:
                pass

    # ------------------------------------------------------------ windows
    def _open_windows_raw(self) -> bool:
        """Primary Windows path: keys AND mouse as raw console INPUT_RECORDs
        via ReadConsoleInputW - no escape-sequence munging at all."""
        try:
            import ctypes

            k = ctypes.windll.kernel32
            h_in = k.GetStdHandle(-10)   # STD_INPUT_HANDLE
            h_out = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode_in = ctypes.c_uint32(0)
            mode_out = ctypes.c_uint32(0)
            if not k.GetConsoleMode(h_in, ctypes.byref(mode_in)):
                return False
            if not k.GetConsoleMode(h_out, ctypes.byref(mode_out)):
                return False
            # EXTENDED 0x0080 | MOUSE_INPUT 0x0010, minus QUICK_EDIT 0x0040
            # (quick-edit would hijack every click as "select for copy").
            new_in = (mode_in.value | 0x0080 | 0x0010) & ~0x0040
            if not k.SetConsoleMode(h_in, new_in):
                return False
            # colors still need processed output + VT sequences
            new_out = mode_out.value | 0x0001 | 0x0004
            k.SetConsoleMode(h_out, new_out)

            SHORT = ctypes.c_short
            USHORT = ctypes.c_ushort
            LONG = ctypes.c_int32
            ULONG = ctypes.c_uint32
            WCHAR = ctypes.c_wchar

            class COORD(ctypes.Structure):
                _fields_ = [("X", SHORT), ("Y", SHORT)]

            class KEY_EVENT_RECORD(ctypes.Structure):
                _fields_ = [
                    ("bKeyDown", LONG), ("wRepeatCount", USHORT),
                    ("wVirtualKeyCode", USHORT), ("wVirtualScanCode", USHORT),
                    ("uChar", WCHAR), ("dwControlKeyState", ULONG),
                ]

            class MOUSE_EVENT_RECORD(ctypes.Structure):
                _fields_ = [
                    ("dwMousePosition", COORD), ("dwButtonState", ULONG),
                    ("dwControlKeyState", ULONG), ("dwEventFlags", ULONG),
                ]

            class EVENT_UNION(ctypes.Union):
                _fields_ = [("KeyEvent", KEY_EVENT_RECORD),
                            ("MouseEvent", MOUSE_EVENT_RECORD)]

            class INPUT_RECORD(ctypes.Structure):
                _fields_ = [("EventType", USHORT), ("Event", EVENT_UNION)]

            if ctypes.sizeof(INPUT_RECORD) != 20:
                return False  # struct layout drifted - don't risk bad reads

            self._win = {
                "hIn": h_in, "hOut": h_out,
                "in_mode": mode_in.value, "out_mode": mode_out.value,
                "k": k, "ctypes": ctypes, "Record": INPUT_RECORD,
            }
            self._prev_buttons = 0
            return True
        except Exception:
            return False

    def _open_windows_msvcrt(self) -> bool:
        """Legacy fallback: msvcrt + VT input (needs SGR mouse flags)."""
        try:
            import ctypes

            k = ctypes.windll.kernel32
            h_in = k.GetStdHandle(-10)   # STD_INPUT_HANDLE
            h_out = k.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode_in = ctypes.c_uint32(0)
            mode_out = ctypes.c_uint32(0)
            if not k.GetConsoleMode(h_in, ctypes.byref(mode_in)):
                return False
            if not k.GetConsoleMode(h_out, ctypes.byref(mode_out)):
                return False
            # EXTENDED 0x0080 | WINDOW_INPUT 0x0008 | MOUSE_INPUT 0x0010
            # | VT_INPUT 0x0200, minus QUICK_EDIT 0x0040 (it eats mouse events)
            new_in = (mode_in.value | 0x0080 | 0x0008 | 0x0010 | 0x0200) & ~0x0040
            if not k.SetConsoleMode(h_in, new_in):
                return False
            # ENABLE_PROCESSED_OUTPUT 0x0001 | ENABLE_VIRTUAL_TERMINAL_PROCESSING 0x0004
            new_out = mode_out.value | 0x0001 | 0x0004
            k.SetConsoleMode(h_out, new_out)
            self._win = {
                "hIn": h_in, "hOut": h_out,
                "in_mode": mode_in.value, "out_mode": mode_out.value,
            }
            import msvcrt

            self._msvcrt = msvcrt
            return True
        except Exception:
            return False

    _WIN_SCAN = {
        "H": "\x1b[A", "P": "\x1b[B", "K": "\x1b[D", "M": "\x1b[C",
        "I": "\x1b[5~", "Q": "\x1b[6~", "G": "\x1b[H", "O": "\x1b[F",
    }

    # ------------------------------------------------------------ reading
    def read_event(self):
        """Block and return one normalized event tuple, or None if closed/eof."""
        if self._mode == "posix":
            return self._read_posix()
        if self._mode == "windows":
            return self._read_windows_raw()
        if self._mode == "windows-msvcrt":
            return self._read_windows()
        try:
            import readchar

            return ("key", normalize_key(readchar.readkey()))
        except Exception:
            return None

    def _read_posix(self):
        import codecs
        import select

        if not hasattr(self, "_dec"):
            self._dec = codecs.getincrementaldecoder("utf-8")("replace")
        os = self._os
        fd = self._fd

        def next_byte(timeout=None):
            r, _, _ = select.select([fd], [], [], timeout)
            if not r:
                return b""
            try:
                return os.read(fd, 1)
            except OSError:
                return b""

        b = next_byte(None)
        if not b:
            return None
        if b != b"\x1b":
            ch = self._dec.decode(b)
            if ch:
                return ("key", ch)
            return self._read_posix()  # still assembling a utf-8 char
        # escape sequence: gather until complete or timeout
        seq = "\x1b"
        while True:
            nxt = next_byte(0.04)
            if not nxt:
                break
            c = nxt.decode("ascii", "ignore")
            if not c:
                break
            seq += c
            if seq.startswith("\x1b[<"):
                if c in ("M", "m"):
                    break
                if len(seq) > 32:
                    break
            elif c in _COMPLETE_FINALS or len(seq) > 8:
                break
        return classify(seq)

    def _read_windows_raw(self):
        """One INPUT_RECORD from ReadConsoleInputW, translated to our event."""
        k = self._win["k"]
        ctypes = self._win["ctypes"]
        Record = self._win["Record"]
        for _ in range(64):  # plenty of room for ignored records (key-up etc.)
            rec = Record()
            got = ctypes.c_ulong(0)
            ok = k.ReadConsoleInputW(self._win["hIn"], ctypes.byref(rec),
                                     1, ctypes.byref(got))
            if not ok or not got.value:
                return None
            ev = self._record_to_event(rec)
            if ev is not None:
                return ev
        return None

    def _record_to_event(self, rec):
        et = rec.EventType
        if et == 0x0001:  # KEY_EVENT
            ke = rec.Event.KeyEvent
            ev_dict = {"type": "key", "down": bool(ke.bKeyDown),
                       "vk": ke.wVirtualKeyCode, "char": ke.uChar}
        elif et == 0x0002:  # MOUSE_EVENT
            me = rec.Event.MouseEvent
            delta = (me.dwButtonState >> 16) & 0xFFFF  # wheel: signed hi-word
            if delta >= 0x8000:
                delta -= 0x10000
            ev_dict = {"type": "mouse",
                       "x": me.dwMousePosition.X, "y": me.dwMousePosition.Y,
                       "buttons": me.dwButtonState & 0xFFFF,
                       "flags": me.dwEventFlags, "delta": delta}
        else:  # window resize / focus / menu: not our business
            return None
        ev, self._prev_buttons = translate_console_record(
            ev_dict, self._prev_buttons)
        return ev

    def _read_windows(self):
        import time

        m = self._msvcrt
        try:
            ch = m.getwch()
        except Exception:
            return None
        if ch in ("\x00", "\xe0"):  # special-key lead byte
            try:
                ch2 = m.getwch()
            except Exception:
                return None
            mapped = self._WIN_SCAN.get(ch2)
            return ("key", mapped) if mapped else None
        if ch == "\x1b":
            seq = ch
            deadline = time.monotonic() + 0.05
            while True:
                if m.kbhit():
                    try:
                        c = m.getwch()
                    except Exception:
                        break
                    seq += c
                    if seq.startswith("\x1b[<"):
                        if c in ("M", "m") or len(seq) > 32:
                            break
                    elif c in _COMPLETE_FINALS or len(seq) > 8:
                        break
                elif time.monotonic() > deadline:
                    break
                else:
                    time.sleep(0.002)
            return classify(seq)
        return ("key", ch)
