"""Общий асинхронный клиент Redis (FSM, кэш PNG; decode_responses=False — бинарные HSET)."""

from __future__ import annotations

import logging

from redis.asyncio import Redis

logger = logging.getLogger("default")

_redis: Redis | None = None


async def init_redis(host: str, port: int) -> Redis | None:
    """Один клиент на процесс: PING; при ошибке — None (MemoryStorage, без кэша)."""
    global _redis
    from redis.asyncio import Redis as RedisCls

    client = RedisCls(host=host, port=port, decode_responses=False)
    try:
        await client.ping()
    except Exception:
        logger.exception("Redis unavailable")
        await client.close()
        _redis = None
        return None
    _redis = client
    logger.info("Redis connected | host=%s | port=%s", host, port)
    return _redis


def detach_redis() -> None:
    """Сбросить ссылку после того, как соединение уже закрыто (например RedisStorage.close())."""
    global _redis
    _redis = None


async def close_redis() -> None:
    """Закрыть соединение (если не передали клиент в RedisStorage — тот закроет сам)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def get_redis() -> Redis | None:
    return _redis
