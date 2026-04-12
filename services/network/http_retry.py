"""Повторы запросов при кратковременных сбоях транспорта (ConnectError, таймауты)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from core.config import get_settings

logger = logging.getLogger("client")

_TRANSIENT_REQUEST_ERRORS: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str | httpx.URL,
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
    **kwargs: Any,
) -> httpx.Response:
    """Выполняет ``client.request`` с экспоненциальной задержкой при транзиентных ошибках."""
    settings = get_settings()
    attempts = (
        max_attempts if max_attempts is not None else settings.http_transient_attempts
    )
    delay = base_delay if base_delay is not None else settings.http_retry_base_delay

    last_exc: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await client.request(method, url, **kwargs)
        except _TRANSIENT_REQUEST_ERRORS as exc:
            last_exc = exc
            if attempt >= attempts:
                logger.error(
                    "HTTP request failed after retries | attempts=%s | method=%s | url=%s | error=%s",
                    attempts,
                    method,
                    url,
                    exc,
                )
                raise
            wait = delay * (2 ** (attempt - 1))
            logger.warning(
                "HTTP transient error, retrying | attempt=%s/%s | method=%s | url=%s | error=%s | sleep_s=%.2f",
                attempt,
                attempts,
                method,
                url,
                exc,
                wait,
            )
            await asyncio.sleep(wait)
    raise AssertionError("unreachable") from last_exc
