"""Тесты повторов HTTP при транзиентных ошибках."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.network import http_retry


@pytest.mark.asyncio
async def test_request_with_retry_retries_then_success() -> None:
    settings = MagicMock()
    settings.http_transient_attempts = 3
    settings.http_retry_base_delay = 0.0

    final = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "https://example.test/"),
    )
    client = MagicMock()
    client.request = AsyncMock(
        side_effect=[
            httpx.ConnectError(
                "boom", request=httpx.Request("GET", "https://example.test/")
            ),
            final,
        ]
    )

    with (
        patch.object(http_retry, "get_settings", return_value=settings),
        patch.object(http_retry.asyncio, "sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        resp = await http_retry.request_with_retry(
            client, "GET", "https://example.test/"
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert client.request.await_count == 2
    mock_sleep.assert_awaited()


@pytest.mark.asyncio
async def test_request_with_retry_exhausts_attempts() -> None:
    settings = MagicMock()
    settings.http_transient_attempts = 2
    settings.http_retry_base_delay = 0.0

    err = httpx.ConnectError(
        "fail", request=httpx.Request("GET", "https://example.test/")
    )
    client = MagicMock()
    client.request = AsyncMock(side_effect=err)

    with (
        patch.object(http_retry, "get_settings", return_value=settings),
        patch.object(http_retry.asyncio, "sleep", new_callable=AsyncMock),
    ):
        with pytest.raises(httpx.ConnectError):
            await http_retry.request_with_retry(client, "GET", "https://example.test/")

    assert client.request.await_count == 2
