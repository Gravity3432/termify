"""GUI logic tests (no display needed - tests pure helpers + wiring)."""
import os, sys
_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)

from termify.gui import _fmt


def test_fmt():
    assert _fmt(0) == "0:00"
    assert _fmt(60000) == "1:00"
    assert _fmt(90061) == "1:30"
    assert _fmt(60_000 * 5) == "5:00"
    print("PASS _fmt")


def test_gui_flag_wired():
    src = open(os.path.join(_parent, "termify", "__main__.py"),
               encoding="utf-8").read()
    assert "--gui" in src
    assert "run_gui" in src
    print("PASS --gui flag wired")


def test_gui_imports():
    from termify.gui import TermifyGUI, run_gui
    assert callable(TermifyGUI) and callable(run_gui)
    print("PASS gui module importable")


def run_all():
    test_fmt()
    test_gui_flag_wired()
    test_gui_imports()
    print("\nALL GUI TESTS PASSED ✅")


if __name__ == "__main__":
    run_all()
