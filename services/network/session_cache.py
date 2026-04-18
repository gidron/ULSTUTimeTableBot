"""Кэш cookies авторизованной сессии УлГТУ в Redis (ключ на учётку, TTL = время жизни сессии).

Позволяет переиспользовать cookies между разными `async with UniversityClient(...)` и между
процессами, чтобы round-robin не форсировал новый логин, пока на аккаунте жива сессия.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from http.cookiejar import Cookie
from typing import Iterable

import httpx

from core.config import get_settings
from core.redis import get_redis

logger = logging.getLogger("client")


@dataclass
class CachedSession:
    """Снимок cookies учётки из Redis."""

    login: str
    saved_at: float
    cookies: list[dict]


def _key(login: str) -> str:
    prefix = get_settings().university_session_cache_key_prefix
    return f"{prefix}:v1:{login}"


def serialize_cookies(jar: Iterable[Cookie]) -> list[dict]:
    """Сериализует httpx/cookiejar Cookies в список dict'ов (то, что нужно для восстановления)."""
    result: list[dict] = []
    for c in jar:
        result.append(
            {
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires,
                "secure": bool(c.secure),
            }
        )
    return result


def hydrate_cookies(client: httpx.AsyncClient, cookies: list[dict]) -> int:
    """Кладёт сохранённые cookies в jar переданного клиента. Возвращает число успешно добавленных."""
    added = 0
    for item in cookies:
        try:
            name = item["name"]
            value = item["value"]
        except (KeyError, TypeError):
            continue
        domain = item.get("domain") or ""
        path = item.get("path") or "/"
        try:
            client.cookies.set(name, value, domain=domain, path=path)
            added += 1
        except Exception:
            logger.debug(
                "Failed to hydrate cookie | name=%s | domain=%s | path=%s",
                name,
                domain,
                path,
                exc_info=True,
            )
    return added


async def load(login: str) -> CachedSession | None:
    """Достать закэшированную сессию по login. None если отключено / Redis недоступен / ключа нет."""
    settings = get_settings()
    if not settings.university_session_cache_enabled:
        return None
    r = get_redis()
    if r is None:
        return None
    key = _key(login)
    try:
        raw = await r.get(key)
    except Exception:
        logger.exception("Redis GET session cache failed | key=%s", key)
        return None
    if not raw:
        return None
    try:
        if isinstance(raw, (bytes, bytearray)):
            text = raw.decode("utf-8")
        else:
            text = raw
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning("Invalid session cache payload | key=%s", key)
        return None
    cookies = data.get("cookies")
    if not isinstance(cookies, list):
        logger.warning("Session cache payload without cookies list | key=%s", key)
        return None
    saved_at = data.get("saved_at")
    try:
        saved_at_f = float(saved_at) if saved_at is not None else 0.0
    except (TypeError, ValueError):
        saved_at_f = 0.0
    return CachedSession(login=login, saved_at=saved_at_f, cookies=cookies)


async def save(login: str, cookies: list[dict], ttl_seconds: int) -> None:
    """Записать cookies в Redis с TTL. Ошибки Redis — warning, не прерываем вызывающий код."""
    settings = get_settings()
    if not settings.university_session_cache_enabled:
        return
    r = get_redis()
    if r is None:
        return
    if ttl_seconds <= 0:
        logger.debug("Session cache TTL <= 0, skipping save | login=%s", login)
        return
    key = _key(login)
    payload = json.dumps(
        {
            "login": login,
            "saved_at": time.time(),
            "cookies": cookies,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    try:
        await r.set(key, payload, ex=ttl_seconds)
    except Exception:
        logger.exception("Redis SET session cache failed | key=%s", key)


async def invalidate(login: str) -> None:
    """Удалить запись кэша (например после 401)."""
    settings = get_settings()
    if not settings.university_session_cache_enabled:
        return
    r = get_redis()
    if r is None:
        return
    key = _key(login)
    try:
        await r.delete(key)
    except Exception:
        logger.exception("Redis DEL session cache failed | key=%s", key)
