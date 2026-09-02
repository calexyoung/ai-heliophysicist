"""HTTP cache behavior: keys, secrets, modes. Fully offline."""

import json

import pytest

from helio_agent import http as hhttp


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(hhttp, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.delenv("HELIO_CACHE_MODE", raising=False)


def test_key_is_stable_and_order_independent():
    a = hhttp.cache_key("https://x.test/api", {"b": 2, "a": 1})
    b = hhttp.cache_key("https://x.test/api", {"a": 1, "b": 2})
    assert a == b and len(a) == 64


def test_secrets_excluded_from_key():
    with_key = hhttp.cache_key("https://x.test/api", {"q": "sun", "api_key": "SECRET"})
    without = hhttp.cache_key("https://x.test/api", {"q": "sun"})
    assert with_key == without


def test_readonly_miss_raises():
    import os
    os.environ["HELIO_CACHE_MODE"] = "readonly"
    with pytest.raises(hhttp.CacheMiss):
        hhttp.cached_get("https://never.cached.test/x")


def test_roundtrip_and_secret_free_disk(monkeypatch):
    calls = {"n": 0}

    class FakeResp:
        status_code = 200
        content = b'{"ok": true}'
        url = "https://x.test/api?q=sun"

    def fake_get(url, params=None, headers=None, timeout=None):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr(hhttp.requests, "get", fake_get)
    r1 = hhttp.cached_get("https://x.test/api", {"q": "sun", "token": "HUSH"})
    r2 = hhttp.cached_get("https://x.test/api", {"q": "sun", "token": "HUSH"})
    assert calls["n"] == 1 and not r1.from_cache and r2.from_cache
    assert r2.json() == {"ok": True}
    stored = list(hhttp.CACHE_DIR.rglob("*.json"))
    assert stored and "HUSH" not in stored[0].read_text()


def test_touched_keys_collected():
    hhttp.reset_touched()
    key = hhttp.cache_key("https://x.test/a")
    try:
        import os
        os.environ["HELIO_CACHE_MODE"] = "readonly"
        hhttp.cached_get("https://x.test/a")
    except hhttp.CacheMiss:
        pass
    assert hhttp.touched_keys() == [key]
