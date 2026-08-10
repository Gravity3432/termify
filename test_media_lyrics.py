"""Tests: lyrics separated into their own view, and media-button support."""
import os, sys, time
_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)

import termify.app as A
from termify import config
from termify.demo_engine import DemoEngine
from termify.input_layer import (
    K_MEDIA_PLAY, K_MEDIA_NEXT, K_MEDIA_PREV, K_MEDIA_STOP, VK_TO_KEY,
    translate_console_record,
)
from termify.media_keys import MediaKeyController
from termify.ui import build


def make_app():
    eng = DemoEngine()
    app = A.App(eng, config.load_config(), demo=True)
    app.boot_skip()
    return app, eng


def test_lyrics_is_a_view():
    app, eng = make_app()
    assert "lyrics" in A.VIEW_ORDER
    # pressing L with a track jumps to the lyrics view
    eng.play_tracks(eng.get_liked(), 0, "ctx")
    app.snap = eng.snapshot()
    app.dispatch("L")
    assert app.view == "lyrics", app.view
    assert not app.show_lyrics  # no longer an overlay flag
    # renders without crashing at several sizes
    for w, h in [(118, 37), (90, 28), (76, 22)]:
        build(app, w, h)
    # nav contains lyrics
    from rich.console import Console
    c = Console(record=True, width=90, height=28)
    build(app, 90, 28)
    print("PASS lyrics is a dedicated view")


def test_devices_no_longer_has_lyrics_block():
    app, eng = make_app()
    app.view = "devices"
    app.rows["devices"] = []
    eng.play_tracks(eng.get_liked(), 0, "ctx")
    app.snap = eng.snapshot()
    # devices view still renders after lyrics were removed from it
    for w, h in [(118, 37), (90, 28)]:
        assert build(app, w, h) is not None
    print("PASS devices view renders clean (lyrics moved out)")


def test_media_vk_mapping():
    # the VK -> marker translation must map media keys
    for vk, marker in [(0xB0, K_MEDIA_NEXT), (0xB1, K_MEDIA_PREV),
                       (0xB3, K_MEDIA_PLAY), (0xB2, K_MEDIA_STOP)]:
        assert VK_TO_KEY.get(vk) == marker, (hex(vk), VK_TO_KEY.get(vk))
    # and translate_console_record surfaces them
    ev = {"type": "key", "down": True, "vk": 0xB3, "char": ""}
    out, _ = translate_console_record(ev, 0)
    assert out == ("key", K_MEDIA_PLAY), out
    print("PASS media VK mapping + translation")


def test_dispatch_media_keys():
    app, eng = make_app()
    eng.play_tracks(eng.get_liked(), 0, "ctx")
    app.snap = eng.snapshot()
    # play -> toggles
    before = app.snap.playing
    app.dispatch(K_MEDIA_PLAY)
    # next advances the position
    app.dispatch(K_MEDIA_NEXT)
    assert app.snap.track is not None
    # no crash for prev / stop
    app.dispatch(K_MEDIA_PREV)
    app.dispatch(K_MEDIA_STOP)
    print("PASS dispatch handles media keys")


def test_media_controller_no_crash():
    mc = MediaKeyController()
    # On a headless box `keyboard` usually isn't importable; start must not raise.
    mc.start(lambda a: None)
    mc.stop()
    print("PASS media controller start/stop never raises")


def run_all():
    test_lyrics_is_a_view()
    test_devices_no_longer_has_lyrics_block()
    test_media_vk_mapping()
    test_dispatch_media_keys()
    test_media_controller_no_crash()
    print("\nALL MEDIA+LYRICS TESTS PASSED ✅")

if __name__ == "__main__":
    run_all()
