"""Friendly-error regression tests."""
import os, sys
_parent = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _parent)
from termify.app import _friendly_api_error


class FakeExc(Exception):
    def __init__(self, msg, status=None):
        self.http_status = status
        super().__init__(msg)


def test_token_error():
    m = _friendly_api_error(FakeExc("token expired", 401))
    assert "setup" in m and "reconnect" in m, m
    print("PASS token/401 -> reconnect hint")


def test_premium_error():
    m = _friendly_api_error(FakeExc("premium required", 403))
    assert "Premium" in m, m
    print("PASS 403 -> premium")


def test_no_device():
    m = _friendly_api_error(FakeExc("device not found", 404))
    assert "device" in m, m
    print("PASS 404 -> no device")


def test_rate_limit():
    m = _friendly_api_error(FakeExc("rate", 429))
    assert "rate limit" in m, m
    print("PASS 429 -> rate limit")


def test_network():
    assert "internet" in _friendly_api_error(ConnectionError("timed out"))
    assert "internet" in _friendly_api_error(TimeoutError())
    print("PASS network errors -> internet hint")


def test_generic_trimmed():
    m = _friendly_api_error(FakeExc("some spotify request error\n  http 500 whoops"))
    assert "traceback" not in m.lower()
    print("PASS generic error trimmed")


def test_empty():
    assert _friendly_api_error(FakeExc("")) == "FakeExc"
    print("PASS empty error -> class name")


def run_all():
    test_token_error()
    test_premium_error()
    test_no_device()
    test_rate_limit()
    test_network()
    test_generic_trimmed()
    test_empty()
    print("\nALL ERROR TESTS PASSED ✅")


if __name__ == "__main__":
    run_all()
