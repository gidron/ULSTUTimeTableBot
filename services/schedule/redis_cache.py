"""Кэш готовых PNG расписания в Redis (HASH: png, filename, week_range)."""

from __future__ import annotations

import hashlib
import logging
from datetime import date

from core.config import get_settings
from core.redis import get_redis

logger = logging.getLogger("default")

_H_PNG = b"png"
_H_FILENAME = b"filename"
_H_WEEK_RANGE = b"week_range"


def schedule_group_hash(group_name: str) -> str:
    """Стабильный идентификатор группы/преподавателя для ключа и SCAN-инвалидации."""
    return hashlib.sha256(group_name.encode("utf-8")).hexdigest()


def build_schedule_cache_key(
    group_name: str,
    week_kind: str,
    local_date: date,
    scope: str,
) -> str:
    """Ключ: префикс, хэш группы, scope (group|teacher), вид недели, календарный день."""
    settings = get_settings()
    gh = schedule_group_hash(group_name)
    d = local_date.isoformat()
    return f"{settings.schedule_cache_key_prefix}:v1:{gh}:{scope}:{week_kind}:{d}"


async def get_cached_schedule_image(
    group_name: str,
    week_kind: str,
    local_date: date,
    scope: str,
) -> tuple[bytes, str, str] | None:
    settings = get_settings()
    if not settings.schedule_cache_enabled:
        return None
    r = get_redis()
    if r is None:
        return None
    key = build_schedule_cache_key(group_name, week_kind, local_date, scope)
    try:
        raw = await r.hgetall(key)
    except Exception:
        logger.exception("Redis HGETALL failed | key=%s", key)
        return None
    if not raw:
        return None
    try:
        png = raw[_H_PNG]
        filename = raw[_H_FILENAME].decode("utf-8")
        week_range = raw[_H_WEEK_RANGE].decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        logger.warning("Invalid schedule cache entry | key=%s", key)
        return None
    return png, filename, week_range


async def set_cached_schedule_image(
    group_name: str,
    week_kind: str,
    local_date: date,
    scope: str,
    image_bytes: bytes,
    filename: str,
    week_range: str,
) -> None:
    settings = get_settings()
    if not settings.schedule_cache_enabled:
        return
    r = get_redis()
    if r is None:
        return
    key = build_schedule_cache_key(group_name, week_kind, local_date, scope)
    ttl = settings.schedule_cache_ttl_seconds
    try:
        pipe = r.pipeline(transaction=True)
        pipe.hset(
            key,
            mapping={
                _H_PNG: image_bytes,
                _H_FILENAME: filename.encode("utf-8"),
                _H_WEEK_RANGE: week_range.encode("utf-8"),
            },
        )
        pipe.expire(key, ttl)
        await pipe.execute()
    except Exception:
        logger.exception("Redis HSET schedule cache failed | key=%s", key)


async def invalidate_group_schedule_cache(group_name: str) -> None:
    """Удалить все ключи кэша расписания для учебной группы (по хэшу имени)."""
    settings = get_settings()
    if not settings.schedule_cache_enabled:
        return
    r = get_redis()
    if r is None:
        return
    gh = schedule_group_hash(group_name)
    pattern = f"{settings.schedule_cache_key_prefix}:v1:{gh}:*"
    cursor: int = 0
    deleted = 0
    try:
        while True:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=64)
            if keys:
                deleted += await r.delete(*keys)
            if cursor == 0:
                break
        if deleted:
            logger.info(
                "Schedule image cache invalidated | group=%s | keys_deleted=%s",
                group_name,
                deleted,
            )
    except Exception:
        logger.exception(
            "Redis invalidate schedule cache failed | group=%s", group_name
        )
