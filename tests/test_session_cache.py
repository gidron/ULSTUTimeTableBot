"""Кэш cookies авторизованной сессии УлГТУ в Redis."""

from __future__ import annotations

import json
import time

import httpx
import pytest

from core.config import get_settings
from core.redis import get_redis
from services.network import session_cache


class _FakeRedis:
    """Минимальный in-memory Redis для теста: get / set(ex=...) / delete."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    async def set(self, key: str, value: bytes, *, ex: int | None = None) -> None:
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttls.pop(key, None)
                removed += 1
        return removed


@pytest.fixture
def fake_redis(monkeypatch):
    fake = _FakeRedis()
    import core.redis as redis_module

    monkeypatch.setattr(redis_module, "_redis", fake)
    yield fake
    monkeypatch.setattr(redis_module, "_redis", None)


@pytest.fixture(autouse=True)
def _settings_cache_clear():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_save_and_load_roundtrip(fake_redis):
    cookies = [
        {
            "name": "session",
            "value": "abc",
            "domain": "time.ulstu.ru",
            "path": "/",
            "expires": None,
            "secure": True,
        }
    ]
    await session_cache.save("login1", cookies, ttl_seconds=600)

    cached = await session_cache.load("login1")
    assert cached is not None
    assert cached.login == "login1"
    assert cached.cookies == cookies
    assert cached.saved_at <= time.time()

    key = f"{get_settings().university_session_cache_key_prefix}:v1:login1"
    assert fake_redis.ttls.get(key) == 600


@pytest.mark.asyncio
async def test_load_returns_none_when_missing(fake_redis):
    cached = await session_cache.load("ghost")
    assert cached is None


@pytest.mark.asyncio
async def test_invalidate_removes_entry(fake_redis):
    await session_cache.save("u1", [{"name": "a", "value": "b"}], ttl_seconds=60)
    assert await session_cache.load("u1") is not None
    await session_cache.invalidate("u1")
    assert await session_cache.load("u1") is None


@pytest.mark.asyncio
async def test_save_is_noop_when_cache_disabled(monkeypatch, fake_redis):
    monkeypatch.setenv("UNIVERSITY_SESSION_CACHE_ENABLED", "false")
    get_settings.cache_clear()
    await session_cache.save("u1", [{"name": "a", "value": "b"}], ttl_seconds=60)
    assert fake_redis.store == {}


@pytest.mark.asyncio
async def test_load_returns_none_when_cache_disabled(monkeypatch, fake_redis):
    key = f"{get_settings().university_session_cache_key_prefix}:v1:u1"
    fake_redis.store[key] = json.dumps(
        {"cookies": [], "saved_at": 0.0, "login": "u1"}
    ).encode()

    monkeypatch.setenv("UNIVERSITY_SESSION_CACHE_ENABLED", "false")
    get_settings.cache_clear()

    assert await session_cache.load("u1") is None


@pytest.mark.asyncio
async def test_load_ignores_invalid_json(fake_redis):
    key = f"{get_settings().university_session_cache_key_prefix}:v1:u1"
    fake_redis.store[key] = b"not-json"
    assert await session_cache.load("u1") is None


@pytest.mark.asyncio
async def test_load_ignores_payload_without_cookies_list(fake_redis):
    key = f"{get_settings().university_session_cache_key_prefix}:v1:u1"
    fake_redis.store[key] = json.dumps({"cookies": "oops"}).encode()
    assert await session_cache.load("u1") is None


@pytest.mark.asyncio
async def test_noop_without_redis():
    # get_redis() is None by default in tests (fixture not used)
    assert get_redis() is None
    assert await session_cache.load("anybody") is None
    await session_cache.save("anybody", [{"name": "x", "value": "y"}], ttl_seconds=10)
    await session_cache.invalidate("anybody")


def test_serialize_and_hydrate_roundtrip():
    src = httpx.AsyncClient()
    src.cookies.set("session", "abc", domain="time.ulstu.ru", path="/")
    src.cookies.set("csrf", "xyz", domain="lk.ulstu.ru", path="/")

    cookies = session_cache.serialize_cookies(src.cookies.jar)
    names = {c["name"] for c in cookies}
    assert names == {"session", "csrf"}

    dst = httpx.AsyncClient()
    added = session_cache.hydrate_cookies(dst, cookies)
    assert added == 2

    dst_pairs = {(c.name, c.domain) for c in dst.cookies.jar}
    assert ("session", "time.ulstu.ru") in dst_pairs
    assert ("csrf", "lk.ulstu.ru") in dst_pairs
