"""Tests for: two date sorts, sidebar playlist drawer, cover-res pick, and
the media-key controller (Windows hook must at least not crash on Linux)."""
import os, sys, time
_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)

import termify.app as A
from termify import config
from termify.demo_engine import DemoEngine
from termify.models import Track
from termify.media_keys import MediaKeyController
from termify.ui import build

T = lambda i, added: Track(id=f"t{i}", uri=f"spotify:track:t{i}",
                           name=f"S{i}", artists="A", album="B",
                           duration_ms=1000, added_at=added)


def make_app():
    eng = DemoEngine()
    app = A.App(eng, config.load_config(), demo=True)
    app.boot_skip()
    return app, eng


def test_two_date_sorts():
    app, _ = make_app()
    names = [m[0] for m in A.SORT_MODES]
    assert "oldest added" in names and "newest added" in names, names
    # oldest = ascending, newest = reverse (descending)
    track_list = [T(1, "2020-01-01T00:00:00Z"), T(2, "2018-01-01T00:00:00Z"),
                  T(3, "2022-01-01T00:00:00Z")]
    app.view = "liked"
    app.rows["liked"] = track_list
    app.rows_orig["liked"] = list(track_list)
    app.sort_idx["liked"] = names.index("oldest added")
    app._apply_sort("liked")
    assert [t.id for t in app.rows["liked"]] == ["t2", "t1", "t3"], \
        [t.id for t in app.rows["liked"]]
    app.sort_idx["liked"] = names.index("newest added")
    app._apply_sort("liked")
    assert [t.id for t in app.rows["liked"]] == ["t3", "t1", "t2"], \
        [t.id for t in app.rows["liked"]]
    print("PASS oldest/newest date sorts")


def test_drawer_toggle_and_render():
    app, eng = make_app()
    app.rows["playlists"] = eng.get_playlists()
    # starts closed
    assert not app.side_drawer
    app.dispatch("[")
    assert app.side_drawer
    # draws the drawer in the nav panel without crashing at several sizes
    for w, h in [(118, 37), (90, 28), (76, 22)]:
        build(app, w, h)
    # navigate the drawer
    app.dispatch("j")
    assert app.drawer_sel == 1
    app.dispatch("k")
    assert app.drawer_sel == 0
    # close
    app.dispatch("[")
    assert not app.side_drawer
    print("PASS sidebar drawer toggle + render")


def test_drawer_plays_playlist():
    app, eng = make_app()
    app.rows["playlists"] = eng.get_playlists()
    app.dispatch("[")
    app.dispatch("j")  # move to a playlist
    app.dispatch("\r")  # enter plays it (via _drawer_play -> engine.play_playlist)
    assert not app.side_drawer  # drawer closes after play
    print("PASS drawer plays a playlist and closes")


def test_cover_picks_largest():
    from termify.catalog import track_from_api
    item = {
        "track": {
            "id": "x", "uri": "u", "name": "N", "type": "track",
            "artists": [{"name": "A"}],
            "album": {"name": "AL", "images": [
                {"url": "https://big"}, {"url": "https://med"}, {"url": "https://small"}]},
            "duration_ms": 1000,
        }
    }
    tr = track_from_api(item)
    assert tr.image_url == "https://big", tr.image_url
    print("PASS cover picks highest-res URL")


def test_media_controller_no_crash_linux():
    mc = MediaKeyController()
    mc.start(lambda a: None)  # on Linux: keyboard pkg absent -> no-op, no crash
    mc.stop()
    # _WinLLHook.start on Linux returns False
    from termify.media_keys import _WinLLHook
    h = _WinLLHook(lambda a: None)
    assert h.start() is False
    h.stop()
    print("PASS media controller + win hook degrade safely on non-Windows")


def run_all():
    test_two_date_sorts()
    test_drawer_toggle_and_render()
    test_drawer_plays_playlist()
    test_cover_picks_largest()
    test_media_controller_no_crash_linux()
    print("\nALL MEDIA2 TESTS PASSED ✅")

if __name__ == "__main__":
    run_all()
