"""TTL 디스크 캐시 검증 (아키텍처 §4.3)."""

import pytest

from soccermind.data.cache import DiskCache


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_set_and_get_within_ttl(tmp_path):
    clock = FakeClock()
    c = DiskCache(tmp_path, clock=clock)
    c.set("k", {"v": 1})
    assert c.get("k", ttl_sec=100) == {"v": 1}


def test_get_miss_returns_none(tmp_path):
    c = DiskCache(tmp_path, clock=FakeClock())
    assert c.get("absent", ttl_sec=100) is None


def test_ttl_expiry(tmp_path):
    clock = FakeClock(1000.0)
    c = DiskCache(tmp_path, clock=clock)
    c.set("k", "payload")
    clock.t = 1000.0 + 50
    assert c.get("k", ttl_sec=100) == "payload"  # 아직 유효
    clock.t = 1000.0 + 150
    assert c.get("k", ttl_sec=100) is None  # 만료


def test_get_or_fetch_calls_loader_once(tmp_path):
    c = DiskCache(tmp_path, clock=FakeClock())
    calls = {"n": 0}

    def loader():
        calls["n"] += 1
        return "fresh"

    assert c.get_or_fetch("k", 100, loader) == "fresh"
    assert c.get_or_fetch("k", 100, loader) == "fresh"  # 캐시 적중
    assert calls["n"] == 1


def test_get_or_fetch_falls_back_to_stale_on_loader_error(tmp_path):
    clock = FakeClock(1000.0)
    c = DiskCache(tmp_path, clock=clock)
    c.set("k", "old")
    clock.t = 1000.0 + 10_000  # 만료시킴

    def failing_loader():
        raise RuntimeError("network down")

    # 만료됐지만 loader 실패 → 만료 캐시로 폴백
    assert c.get_or_fetch("k", 100, failing_loader) == "old"


def test_get_or_fetch_reraises_when_no_stale(tmp_path):
    c = DiskCache(tmp_path, clock=FakeClock())

    def failing_loader():
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        c.get_or_fetch("k", 100, failing_loader)
