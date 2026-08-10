"""Global keyboard media-button hook.

Routes the keyboard's play/pause / next / previous keys to Termify even when
the terminal window is NOT focused.

Two strategies, tried in order:

1. **Windows low-level keyboard hook** (SetWindowsHookEx / WH_KEYBOARD_LL)
   - Captures media keys system-wide with NO admin rights and no extra pip
     package. This is the standard way media players do it. Runs its own
     message loop on a background thread.
2. **`keyboard` package** (Windows/X11) - optional fallback if the native hook
   is unavailable for any reason.

If both fail, media buttons still work *inside* the focused terminal via the
VK/sequence mapping in input_layer.py.

Everything here is best-effort: any failure just means no global keys, never a
crash.
"""
from __future__ import annotations
import sys
import threading
from typing import Callable, Optional

# media VK codes used on Windows
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2


class _WinLLHook:
    """A global WH_KEYBOARD_LL hook using only ctypes (no admin)."""

    def __init__(self, on_event: Callable[[str], None]):
        self._on_event = on_event
        self._hhook = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._err: Optional[Exception] = None

    # ---- ctypes types (built lazily so importing is safe off-Windows) ----
    @staticmethod
    def _ctypes():
        import ctypes
        from ctypes import wintypes

        return ctypes, wintypes

    def start(self) -> bool:
        try:
            return self._start()
        except Exception as exc:  # noqa: BLE001
            self._err = exc
            return False

    def _start(self) -> bool:
        if sys.platform != "win32":
            return False
        import ctypes
        from ctypes import wintypes

        WH_KEYBOARD_LL = 13
        WM_KEYDOWN = 0x0100
        WM_SYSKEYDOWN = 0x0104
        LLKHF_INJECTED = 0x10

        VK_TO_ACTION = {
            VK_MEDIA_PLAY_PAUSE: "play",
            VK_MEDIA_NEXT: "next",
            VK_MEDIA_PREV: "prev",
            VK_MEDIA_STOP: "stop",
        }

        # KBDLLHOOKSTRUCT layout (x64: DWORDs then POINTER-aligned)
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", wintypes.DWORD),
                    ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
                ]
        else:
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", wintypes.DWORD),
                    ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", wintypes.ULONG),
                ]

        HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
        )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        GetModuleHandleW = kernel32.GetModuleHandleW
        GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        GetModuleHandleW.restype = wintypes.HMODULE
        SetWindowsHookExW = user32.SetWindowsHookExW
        SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, wintypes.HMODULE, wintypes.DWORD]
        SetWindowsHookExW.restype = wintypes.HHOOK
        CallNextHookEx = user32.CallNextHookEx
        CallNextHookEx.argtypes = [
            wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        CallNextHookEx.restype = ctypes.c_long
        UnhookWindowsHookEx = user32.UnhookWindowsHookEx
        UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        UnhookWindowsHookEx.restype = wintypes.BOOL
        GetMessageW = user32.GetMessageW
        GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT]
        GetMessageW.restype = wintypes.BOOL
        TranslateMessage = user32.TranslateMessage
        DispatchMessageW = user32.DispatchMessageW

        owner = self

        @HOOKPROC
        def hook_proc(nCode, wParam, lParam):
            if nCode == 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                try:
                    kh = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    vk = int(kh.vkCode)
                    # ignore injected events so a macro/keyboard software
                    # doesn't double-trigger (and so we don't recurse)
                    if not (kh.flags & LLKHF_INJECTED) and vk in VK_TO_ACTION:
                        owner._on_event(VK_TO_ACTION[vk])
                        return 1  # swallow - don't let anything else see it
                except Exception:  # noqa: BLE001
                    pass
            return CallNextHookEx(None, nCode, wParam, lParam)

        def message_loop():
            try:
                hmod = GetModuleHandleW(None)
                hook = SetWindowsHookExW(
                    WH_KEYBOARD_LL, hook_proc, hmod, 0)  # 0 = global
                if not hook:
                    owner._err = ctypes.WinError(ctypes.get_last_error())
                    owner._ready.set()
                    return
                owner._hhook = hook
                owner._ready.set()
                msg = wintypes.MSG()
                while GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    TranslateMessage(ctypes.byref(msg))
                    DispatchMessageW(ctypes.byref(msg))
            except Exception as exc:  # noqa: BLE001
                owner._err = exc
                owner._ready.set()

        self._thread = threading.Thread(target=message_loop, daemon=True,
                                        name="termify-mediahook")
        self._thread.start()
        self._ready.wait(timeout=3.0)
        return self._hhook is not None

    def stop(self) -> None:
        if self._hhook is not None:
            try:
                import ctypes
                user32 = ctypes.WinDLL("user32")
                user32.UnhookWindowsHookEx(self._hhook)
            except Exception:  # noqa: BLE001
                pass
            self._hhook = None


class MediaKeyController:
    """Global media-key hook: native Windows hook, then keyboard-pkg fallback."""

    def __init__(self):
        self._hook = None
        self._kb_listener = None
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def start(self, on_event: Callable[[str], None]) -> None:
        # 1) native Windows low-level hook (no admin, no pip package)
        if sys.platform == "win32":
            hook = _WinLLHook(on_event)
            if hook.start():
                self._hook = hook
                self._enabled = True
                return
        # 2) keyboard package fallback
        try:
            import keyboard  # optional
        except Exception:
            return
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
            self._kb_listener = handlers
            self._enabled = True
        except Exception:
            self._kb_listener = None
            self._enabled = False

    def stop(self) -> None:
        if self._hook is not None:
            self._hook.stop()
            self._hook = None
        if self._kb_listener:
            try:
                import keyboard
                for h in self._kb_listener:
                    keyboard.remove_hotkey(h)
            except Exception:
                pass
            self._kb_listener = None
        self._enabled = False
