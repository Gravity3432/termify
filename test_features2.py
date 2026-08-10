"""Tests for the new feature batch:
  - local listening stats + weekly report (termify/stats.py)
  - play next / play later queue insertion (stream & demo engines)
  - duplicate finder (catalog.find_duplicates)
  - app-level dup toggle & stats overlay render
"""
import os, sys, tempfile
from pathlib import Path

_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)

from termify.stats import Stats, fmt_ms
from termify.models import Track
from termify.catalog import Catalog
from termify.demo_engine import DemoEngine

T = lambda i, dur=1000: Track(id=f"t{i}", uri=f"spotify:track:t{i}",
                               name=f"Song {i}", artists=f"Artist {i}",
                               album=f"Album {i}", duration_ms=dur)

# ---------------------------------------------------------------- stats
def test_stats_recording_and_queries():
    d = tempfile.mkdtemp()
    p = Path(d) / "stats.json"
    s = Stats(p)
    # record some plays across 'days' (simulate by injecting into days map)
    from datetime import date, timedelta
    today = date.today()
    for i in range(3):  # today: track1 5s
        s.add_play(T(1), 2000)
    s.add_play(T(2), 3000)  # today: track2 3s
    assert s.ms_today() >= 5000
    assert s.ms_all() == s.ms_today()  # only today recorded
    # streak: today has data -> >=1
    assert s.streak_days() >= 1
    top = s.top_tracks(1)
    assert top[0][0] == "Song 1"  # 6000ms > 3000ms
    s.save()
    s2 = Stats(p)  # reload from disk
    assert s2.ms_today() == s.ms_today()
    print("PASS stats recording/queries/save")

def test_stats_weekly_report():
    d = tempfile.mkdtemp()
    s = Stats(Path(d) / "s.json")
    s.add_play(T(7), 7000)
    s.add_play(T(8), 4000)
    r = s.weekly_report()
    assert r["minutes"] == (s.ms_period(7) // 60000)
    assert r["top_tracks"][0][0] == "Song 7"
    assert len(r["top_artists"]) >= 1
    print("PASS stats weekly report")

def test_fmt_ms():
    assert fmt_ms(65_000) == "1m 05s"
    assert fmt_ms(3_700_000).startswith("1h")
    assert fmt_ms(3000) == "3s"
    print("PASS fmt_ms")

def test_stats_corrupt_file_resilient():
    d = tempfile.mkdtemp()
    p = Path(d) / "s.json"
    p.write_text("{ not json !!")
    s = Stats(p)
    assert s.ms_all() == 0  # doesn't crash
    print("PASS stats corrupt-file resilience")

# ---------------------------------------------------------------- queue insert
def test_demo_queue_insert():
    e = DemoEngine()
    tracks = [T(1), T(2), T(3), T(4)]
    e.play_tracks(tracks, 0, "ctx")  # order [0,1,2,3], pos=0
    # play next a NEW track
    e.queue_insert(T(9), to_end=False)
    assert e.snapshot().queue[0].id == "t9", "new track should be up next"
    # queue at end
    e.queue_insert(T(8), to_end=True)
    q = e.snapshot().queue
    assert q[-1].id == "t8"
    # jump to the "next" one
    e.queue_play(0)
    assert e.snapshot().track.id == "t9"
    print("PASS demo queue_insert play-next/later")

def test_catalog_find_duplicates():
    tracks = [T(1), T(2), T(1), T(3), T(2), T(4)]
    dupes = Catalog.find_duplicates(tracks)
    assert [x.id for x in dupes] == ["t1", "t2"]
    assert Catalog.find_duplicates([T(1), T(2)]) == []
    print("PASS catalog.find_duplicates")

# ---------------------------------------------------------------- app-level render
def test_stats_overlay_renders():
    from rich.console import Console
    import termify.app as A
    from termify import config
    eng = DemoEngine()
    app = A.App(eng, config.load_config(), demo=True)
    app.boot_skip()
    app.show_stats = True
    # feed it a track + some stats so it has content
    app.snap = eng.snapshot()
    app.stats.add_play(T(1), 60_000)
    W, H = 118, 37
    # render every view + overlays to catch crashes
    from termify.ui import build, render_stats
    for _ in range(5):
        build(app, W, H)
    # verify dup toggle path via catalog
    app.view = "liked"
    app.rows["liked"] = [T(1), T(1), T(2)]
    app.sel["liked"] = 0
    app._toggle_duplicates()
    assert app._dupes_active and len(app.rows["liked"]) == 1
    app._toggle_duplicates()
    assert len(app.rows["liked"]) == 3
    print("PASS stats overlay + dup toggle render")

def run_all():
    test_stats_recording_and_queries()
    test_stats_weekly_report()
    test_fmt_ms()
    test_stats_corrupt_file_resilient()
    test_demo_queue_insert()
    test_catalog_find_duplicates()
    test_stats_overlay_renders()
    print("\nALL FEATURE TESTS PASSED ✅")

if __name__ == "__main__":
    run_all()
