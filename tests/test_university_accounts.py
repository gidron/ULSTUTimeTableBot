"""Пул учёток УлГТУ и round-robin селектор."""

from __future__ import annotations

import json

import pytest

from core.config import get_settings
from services.network.account_selector import (
    UniversityAccountSelector,
    get_university_account_selector,
    reset_university_account_selector,
)
from services.network.exceptions import UniversityAuthError
from services.network import university_client as university_client_module
from services.network.session_provider import UniversitySessionProvider


@pytest.fixture(autouse=True)
def _clear_settings_and_selector():
    get_settings.cache_clear()
    reset_university_account_selector()
    yield
    get_settings.cache_clear()
    reset_university_account_selector()


def test_credentials_pool_fallback_when_json_empty(monkeypatch):
    """Без списка аккаунтов — только пара login/password (env перекрывает локальный .env)."""
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", "")
    monkeypatch.setenv("UNIVERSITY_LOGIN", "u")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "p")
    get_settings.cache_clear()
    s = get_settings()
    assert s.university_credentials_pool() == [
        (s.university_login, s.university_password)
    ]


def test_credentials_pool_from_json(monkeypatch):
    accounts = [
        {"login": "a", "password": "1"},
        {"login": "b", "password": "2"},
    ]
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", json.dumps(accounts))
    get_settings.cache_clear()
    s = get_settings()
    assert s.university_credentials_pool() == [("a", "1"), ("b", "2")]


def test_credentials_pool_invalid_json(monkeypatch):
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", "not-json")
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="valid JSON"):
        get_settings().university_credentials_pool()


def test_credentials_pool_empty_array_falls_back(monkeypatch):
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", "[]")
    get_settings.cache_clear()
    s = get_settings()
    assert s.university_credentials_pool() == [
        (s.university_login, s.university_password)
    ]


@pytest.mark.asyncio
async def test_round_robin_in_process():
    pool = [("a", "1"), ("b", "2"), ("c", "3")]
    sel = UniversityAccountSelector(
        pool,
        use_redis=False,
        redis_key="test:rr",
    )
    order = [await sel.pick() for _ in range(7)]
    logins = [x[0] for x in order]
    assert logins == ["a", "b", "c", "a", "b", "c", "a"]


@pytest.mark.asyncio
async def test_round_robin_single_account():
    sel = UniversityAccountSelector(
        [("only", "x")],
        use_redis=False,
        redis_key="test:rr",
    )
    assert await sel.pick() == ("only", "x")
    assert await sel.pick() == ("only", "x")


@pytest.mark.asyncio
async def test_get_selector_uses_settings_pool(monkeypatch):
    accounts = [
        {"login": "u1", "password": "p1"},
        {"login": "u2", "password": "p2"},
    ]
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", json.dumps(accounts))
    get_settings.cache_clear()
    reset_university_account_selector()
    sel = get_university_account_selector()
    assert await sel.pick() == ("u1", "p1")
    assert await sel.pick() == ("u2", "p2")
    assert await sel.pick() == ("u1", "p1")


@pytest.mark.asyncio
async def test_university_client_auth_failover_second_account(monkeypatch):
    accounts = [
        {"login": "u1", "password": "p1"},
        {"login": "u2", "password": "p2"},
    ]
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", json.dumps(accounts))
    monkeypatch.setenv("UNIVERSITY_LOGIN", "")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "")
    get_settings.cache_clear()
    reset_university_account_selector()

    class MockSessionProvider:
        def __init__(
            self,
            group: str,
            login: str,
            password: str,
            timeout: float = 0,
            **kwargs,
        ):
            self.group = group
            self.login = login
            self.password = password

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_authorized_client(self):
            if self.login == "u1":
                raise UniversityAuthError("bad credentials")
            return object()

    monkeypatch.setattr(
        university_client_module,
        "UniversitySessionProvider",
        MockSessionProvider,
    )

    async with university_client_module.UniversityClient("ИВТ-101") as client:
        assert client.session_provider.login == "u2"


@pytest.mark.asyncio
async def test_university_client_auth_failover_all_fail(monkeypatch):
    accounts = [
        {"login": "u1", "password": "p1"},
        {"login": "u2", "password": "p2"},
    ]
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", json.dumps(accounts))
    monkeypatch.setenv("UNIVERSITY_LOGIN", "")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "")
    get_settings.cache_clear()
    reset_university_account_selector()

    class MockSessionProvider:
        def __init__(
            self,
            group: str,
            login: str,
            password: str,
            timeout: float = 0,
            **kwargs,
        ):
            self.login = login

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get_authorized_client(self):
            raise UniversityAuthError("always fail")

    monkeypatch.setattr(
        university_client_module,
        "UniversitySessionProvider",
        MockSessionProvider,
    )

    with pytest.raises(UniversityAuthError, match="always fail"):
        async with university_client_module.UniversityClient("ИВТ-101"):
            pass


@pytest.mark.asyncio
async def test_refresh_authorization_failover_to_second_account(monkeypatch):
    monkeypatch.setenv(
        "UNIVERSITY_ACCOUNTS_JSON",
        json.dumps(
            [
                {"login": "u1", "password": "p1"},
                {"login": "u2", "password": "p2"},
            ]
        ),
    )
    monkeypatch.setenv("UNIVERSITY_LOGIN", "")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "")
    get_settings.cache_clear()

    calls: list[str] = []

    async def fake_do_authorize(self):
        calls.append(self.login)
        if self.login == "u1":
            raise UniversityAuthError("bad")
        self._authorized = True

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1", enable_account_failover=True)
    async with sp:
        await sp.refresh_authorization()

    assert calls == ["u1", "u2"]
    assert sp.login == "u2"


@pytest.mark.asyncio
async def test_refresh_authorization_failover_disabled_raises(monkeypatch):
    monkeypatch.setenv(
        "UNIVERSITY_ACCOUNTS_JSON",
        json.dumps(
            [
                {"login": "u1", "password": "p1"},
                {"login": "u2", "password": "p2"},
            ]
        ),
    )
    monkeypatch.setenv("UNIVERSITY_LOGIN", "")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "")
    get_settings.cache_clear()

    async def fake_do_authorize(self):
        raise UniversityAuthError("bad")

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", "u1", "p1", enable_account_failover=False)
    with pytest.raises(UniversityAuthError, match="bad"):
        async with sp:
            await sp.refresh_authorization()


@pytest.mark.asyncio
async def test_refresh_authorization_failover_no_other_accounts(monkeypatch):
    monkeypatch.setenv("UNIVERSITY_ACCOUNTS_JSON", "")
    monkeypatch.setenv("UNIVERSITY_LOGIN", "only")
    monkeypatch.setenv("UNIVERSITY_PASSWORD", "secret")
    get_settings.cache_clear()

    async def fake_do_authorize(self):
        raise UniversityAuthError("bad")

    monkeypatch.setattr(UniversitySessionProvider, "_do_authorize", fake_do_authorize)

    sp = UniversitySessionProvider("grp", enable_account_failover=True)
    with pytest.raises(UniversityAuthError, match="bad"):
        async with sp:
            await sp.refresh_authorization()
