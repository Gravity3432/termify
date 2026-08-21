"""Tests for mouse click resolution: exact rows + terminal offset snapping.

Reproduces the "clicking bug" where a click on a sidebar/playlist row could
resolve to the row above/below. Guards find_zone and the offset correction.
"""
import sys, os
_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)

from termify.app import App


def make_app_with_sidebar():
    """App-shaped object with sidebar zones at rows 10,11,12 (index 0,1,2)."""
    class H: pass
    h = H()
    h.zones = [
        {"x": 2, "y": 10, "w": 20, "h": 1, "type": "sidebar", "index": 0},
        {"x": 2, "y": 11, "w": 20, "h": 1, "type": "sidebar", "index": 1},
        {"x": 2, "y": 12, "w": 20, "h": 1, "type": "sidebar", "index": 2},
    ]
    h.find_zone = App.find_zone.__get__(h)
    h.mouse_y_offset = 0
    h.mouse_y_scale = 1.0
    def _find(x, y, tol=3):
        cy = y * h.mouse_y_scale + h.mouse_y_offset
        return h.find_zone(x, int(round(cy)), tol)
    h._find_zone = _find
    return h


def test_exact_rows():
    h = make_app_with_sidebar()
    # clicking exactly on each row selects that row (no mis-snap)
    assert h.find_zone(5, 10, 3)["index"] == 0
    assert h.find_zone(5, 11, 3)["index"] == 1
    assert h.find_zone(5, 12, 3)["index"] == 2
    print("PASS exact row clicks select the right sidebar item")


def test_offset_correction():
    # mouse_y_offset shifts which row a raw click resolves to.
    h = make_app_with_sidebar()
    # offset +1: raw y=11 is treated as row 12 -> index 2
    h.mouse_y_offset = 1
    assert h._find_zone(5, 11)["index"] == 2
    # offset -1: raw y=11 is treated as row 10 -> index 0
    h.mouse_y_offset = -1
    assert h._find_zone(5, 11)["index"] == 0
    # offset 0 (default): exact behavior preserved
    h.mouse_y_offset = 0
    assert h._find_zone(5, 11)["index"] == 1
    print("PASS mouse_y_offset shifts click resolution by the right amount")


def test_scale_correction():
    # A growing offset (drift lower-down) needs scale, not just shift.
    h = make_app_with_sidebar()
    h.mouse_y_scale = 1.0
    # with scale=1 and no offset, exact rows are exact
    assert h._find_zone(5, 10)["index"] == 0
    assert h._find_zone(5, 11)["index"] == 1
    # scale < 1 pulls low clicks up: raw y=13 -> row ~11.7 -> row 12
    h.mouse_y_scale = 0.9
    # raw 12 -> 10.8 -> 11 (index 1)
    assert h._find_zone(5, 12)["index"] == 1
    print("PASS mouse_y_scale shrinks low-click resolution")


def test_out_of_range_returns_none():
    h = make_app_with_sidebar()
    assert h.find_zone(5, 50, 3) is None
    assert h.find_zone(50, 11, 3) is None
    print("PASS clicks outside any zone return None")


def run_all():
    test_exact_rows()
    test_offset_correction()
    test_scale_correction()
    test_out_of_range_returns_none()
    print("\nALL MOUSE TESTS PASSED ✅")


if __name__ == "__main__":
    run_all()
