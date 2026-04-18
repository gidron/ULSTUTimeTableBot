"""Интеграция кэша сессии в UniversitySessionProvider: reuse cookies, инвалидация, failover."""

from __future__ import annotations

import json

import pytest

from core.config import get_settings
from services.network.exceptions import UniversityAuthError
from services.network.session_provider import UniversitySessionProvider


class _FakeRedis:
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


def _cookie_key(login: str) -> str:
    return f"{get_settings().university_session_cache_key_prefix}:v1:{login}"


def _prime_cache_with_time_session(fake: _FakeRedis, login: str) -> None:
    payload = {
        "login": login,
        "saved_at": 1.0,
        "cookies": [
            {
                "name": "session",
                "value": "cached-value",
                "domain": "time.ulstu.ru",
                "path": "/",
                "expires": None,
                "secure": True,
            }
        ],
    }
    fake.store[_cookie_key(login)] = json.dumps(payload).encode("utf-8")


@pytest.mark.asyncio
async def test_cached_session_is_reused_without_login(monkeypatch, fake_redis):
    _prime_cache_with_time_session(fake_redis, "u1")

    calls: list[str] = []

    async def fake_do_authorize(self):
        calls.append(self.login)
        self._authorized = True

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1")
    async with sp:
        client = await sp.get_authorized_client()
        assert client is sp._client
        assert sp._authorized is True

    assert calls == [], "Должны использовать кэш, без нового логина"


@pytest.mark.asyncio
async def test_do_authorize_persists_cookies_to_cache(monkeypatch, fake_redis):
    async def fake_do_authorize(self):
        self._authorized = True
        self._client.cookies.set(
            "session", "fresh-value", domain="time.ulstu.ru", path="/"
        )
        await self._persist_session_to_cache()

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1")
    async with sp:
        await sp.get_authorized_client()

    assert _cookie_key("u1") in fake_redis.store
    data = json.loads(fake_redis.store[_cookie_key("u1")])
    names = [c["name"] for c in data["cookies"]]
    assert "session" in names
    assert (
        fake_redis.ttls[_cookie_key("u1")]
        == get_settings().university_session_ttl_seconds
    )


@pytest.mark.asyncio
async def test_refresh_invalidates_cache_and_reauthorizes(monkeypatch, fake_redis):
    _prime_cache_with_time_session(fake_redis, "u1")

    login_calls: list[str] = []

    async def fake_do_authorize(self):
        login_calls.append(self.login)
        self._authorized = True
        self._client.cookies.clear()
        self._client.cookies.set(
            "session", "after-refresh", domain="time.ulstu.ru", path="/"
        )
        await self._persist_session_to_cache()

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1")
    async with sp:
        # Сначала сессия поднялась из кэша — без логина.
        await sp.get_authorized_client()
        assert login_calls == []
        await sp.refresh_authorization()

    assert login_calls == ["u1"], (
        "refresh_authorization должен форсировать полный логин"
    )
    data = json.loads(fake_redis.store[_cookie_key("u1")])
    values = {c["name"]: c["value"] for c in data["cookies"]}
    assert values.get("session") == "after-refresh"


@pytest.mark.asyncio
async def test_failover_invalidates_failed_account_cache(monkeypatch, fake_redis):
    monkeypatch.setenv(
        "UNIVERSITY_ACCOUNTS_JSON",
        json.dumps(
            [
                {"login": "u1", "password": "p1"},
                {"login": "u2", "password": "p2"},
            ]
        ),
    )
    get_settings.cache_clear()

    _prime_cache_with_time_session(fake_redis, "u1")
    _prime_cache_with_time_session(fake_redis, "u2")

    async def fake_do_authorize(self):
        if self.login == "u1":
            raise UniversityAuthError("bad u1")
        self._authorized = True
        self._client.cookies.clear()
        self._client.cookies.set(
            "session", "u2-fresh", domain="time.ulstu.ru", path="/"
        )
        await self._persist_session_to_cache()

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1", enable_account_failover=True)
    async with sp:
        await sp.refresh_authorization()

    assert sp.login == "u2"
    # Кэш u1 убит, кэш u2 обновлён свежими cookies.
    assert _cookie_key("u1") not in fake_redis.store
    data = json.loads(fake_redis.store[_cookie_key("u2")])
    values = {c["name"]: c["value"] for c in data["cookies"]}
    assert values.get("session") == "u2-fresh"


@pytest.mark.asyncio
async def test_cache_without_time_cookie_does_not_mark_authorized(
    monkeypatch, fake_redis
):
    # В кэше только cookies lk.ulstu.ru — для time.ulstu.ru cookie нет, логин обязателен.
    fake_redis.store[_cookie_key("u1")] = json.dumps(
        {
            "login": "u1",
            "saved_at": 1.0,
            "cookies": [
                {
                    "name": "session",
                    "value": "lk-only",
                    "domain": "lk.ulstu.ru",
                    "path": "/",
                }
            ],
        }
    ).encode("utf-8")

    calls: list[str] = []

    async def fake_do_authorize(self):
        calls.append(self.login)
        self._authorized = True
        self._client.cookies.set("session", "v", domain="time.ulstu.ru", path="/")
        await self._persist_session_to_cache()

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1")
    async with sp:
        await sp.get_authorized_client()

    assert calls == ["u1"]


@pytest.mark.asyncio
async def test_cache_disabled_skips_hydration(monkeypatch, fake_redis):
    _prime_cache_with_time_session(fake_redis, "u1")
    monkeypatch.setenv("UNIVERSITY_SESSION_CACHE_ENABLED", "false")
    get_settings.cache_clear()

    calls: list[str] = []

    async def fake_do_authorize(self):
        calls.append(self.login)
        self._authorized = True
        self._client.cookies.set("session", "v", domain="time.ulstu.ru", path="/")

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1")
    async with sp:
        await sp.get_authorized_client()

    assert calls == ["u1"], "Кэш отключён — должен сработать обычный логин"
