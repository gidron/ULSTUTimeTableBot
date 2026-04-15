"""Round-robin выбор пары login/password для запросов к API УлГТУ."""

from __future__ import annotations

import asyncio
import logging

from core.config import get_settings
from core.redis import get_redis

logger = logging.getLogger("client")


class UniversityAccountSelector:
    """Round-robin по списку учёток; опционально общий счётчик в Redis для нескольких процессов."""

    def __init__(
        self,
        pool: list[tuple[str, str]],
        *,
        use_redis: bool,
        redis_key: str,
    ) -> None:
        if not pool:
            raise ValueError("university credentials pool is empty")
        self._pool = pool
        self._n = len(pool)
        self._use_redis = use_redis
        self._redis_key = redis_key
        self._lock = asyncio.Lock()
        self._next_index = 0

    async def pick(self) -> tuple[str, str]:
        if self._n == 1:
            return self._pool[0]

        if self._use_redis:
            client = get_redis()
            if client is not None:
                try:
                    n = await client.incr(self._redis_key)
                    idx = (int(n) - 1) % self._n
                    return self._pool[idx]
                except Exception:
                    logger.exception(
                        "Redis INCR failed for round-robin, falling back to in-process"
                    )

        async with self._lock:
            cred = self._pool[self._next_index]
            self._next_index = (self._next_index + 1) % self._n
            return cred


_selector: UniversityAccountSelector | None = None


def get_university_account_selector() -> UniversityAccountSelector:
    global _selector
    if _selector is None:
        settings = get_settings()
        pool = settings.university_credentials_pool()
        _selector = UniversityAccountSelector(
            pool,
            use_redis=settings.university_accounts_use_redis_round_robin,
            redis_key=settings.university_accounts_redis_counter_key,
        )
    return _selector


def reset_university_account_selector() -> None:
    """Сбросить синглтон (тесты / перезагрузка настроек)."""
    global _selector
    _selector = None
