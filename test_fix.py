"""Sanity tests for the playlist cap + date-added changes."""
import sys, os, types, re
_parent = os.path.dirname(__file__)
sys.path.insert(0, _parent)

from termify.models import Track
from termify.catalog import track_from_api, Catalog

def page_items(entries, total):
    return {"items": entries, "total": total}

def wrap(it, added_at):
    return {"added_at": added_at, "item": it}

def mk_track(i):
    return {
        "id": f"t{i}", "uri": f"spotify:track:t{i}", "name": f"Song {i}",
        "artists": [{"name": f"Artist {i}"}], "album": {"name": f"Album {i}",
        "images": [{"url": "x"}, {"url": "y"}]},
        "duration_ms": 1000 * i, "type": "track",
    }

# ---- 1. added_at captured from wrapper --------------------------------
it = wrap(mk_track(1), "2021-05-04T12:00:00Z")
tr = track_from_api(it)
assert tr is not None and tr.added_at == "2021-05-04T12:00:00Z", tr
assert tr.date_text == "2021-05-04", tr.date_text
assert track_from_api(wrap(mk_track(2), None)).added_at is None
print("PASS track_from_api captures added_at + date_text")

# ---- 2. playlist_tracks pages through the WHOLE list ------------------
class FakeSp:
    def playlist_items(self, pid, limit=100, offset=0, additional_types=("track",)):
        raise RuntimeError("should use _get path")
    def current_user_saved_tracks_contains(self, ids):
        return [False] * len(ids)

c = Catalog(FakeSp())
c._api_token = lambda: "tok"
# 566 tracks, served 100 at a time
all_items = [wrap(mk_track(i), f"2021-01-{i%28+1:02d}T00:00:00Z") for i in range(566)]
def fake_get(url, params):
    offset = params["offset"]
    lim = params["limit"]
    chunk = all_items[offset:offset+lim]
    return page_items(chunk, 566)
c._get = fake_get

got = c.playlist_tracks("pl1")
assert len(got) == 566, f"expected 566, got {len(got)}"
assert got[0].added_at and got[-1].added_at
print("PASS playlist_tracks loads all 566 (not capped at 500)")

# ---- 3. liked songs also pages through the whole list ------------------
liked_items = [wrap(mk_track(i), f"2022-02-{i%28+1:02d}T00:00:00Z") for i in range(750)]
class FakeSp2:
    def current_user_saved_tracks(self, limit=50, offset=0):
        chunk = liked_items[offset:offset+limit]
        return page_items(chunk, 750)
    def current_user_saved_tracks_contains(self, ids):
        return [False] * len(ids)
c2 = Catalog(FakeSp2())
gl = c2.liked()
assert len(gl) == 750, f"expected 750, got {len(gl)}"
print("PASS liked() loads all 750 (not capped at 500)")

# ---- 4. empty/error handling still safe -------------------------------
class FakeSp3:
    def current_user_saved_tracks(self, limit=50, offset=0):
        return {"items": [], "total": 0}
    def current_user_saved_tracks_contains(self, ids):
        return []
c3 = Catalog(FakeSp3())
assert c3.liked() == []
print("PASS empty lists are safe")

# ---- 5. date-added sort key used by the app ---------------------------
src = open(os.path.join(_parent, "termify", "app.py"), encoding="utf-8").read()
assert '"oldest added"' in src and '"newest added"' in src, "app.py SORT_MODES missing date sorts"
m = re.search(r"SORT_MODES\s*=\s*\[(.*?)\]", src, re.S)
modes = m.group(1)
assert "oldest added" in modes and "newest added" in modes
key = lambda t: t.added_at or ""
a = Track(id="a", uri="u", name="A", artists="", album="", duration_ms=1,
          added_at="2021-05-04T00:00:00Z")
b = Track(id="b", uri="u", name="B", artists="", album="", duration_ms=2,
          added_at="2023-01-01T00:00:00Z")
cT = Track(id="c", uri="u", name="C", artists="", album="", duration_ms=3,
           added_at=None)
assert key(a) < key(b), (key(a), key(b))  # 2021 < 2023
print("PASS date-added sort mode registered and ordered")

print("\nALL FIX CHECKS PASSED ✅")
