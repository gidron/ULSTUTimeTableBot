"""Тесты разбора autocomplete для преподавателей."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.network.api_client import UniversityApiClient
from services.network.exceptions import UniversityApiError
from services.network.session_provider import UniversitySessionProvider


@pytest.mark.asyncio
async def test_find_teachers_returns_stripped_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MagicMock(spec=UniversitySessionProvider)
    provider.group = "Вол"
    client = UniversityApiClient(provider)

    async def fake_autocomplete(_value: str) -> dict:
        return {
            "response": {
                "groups": [],
                "rooms": [],
                "teachers": ["  Волкова Е А  ", "Волков М П"],
            },
            "error": "",
        }

    monkeypatch.setattr(client, "autocomplete", fake_autocomplete)
    result = await client.find_teachers("Вол")
    assert result == ["Волкова Е А", "Волков М П"]


@pytest.mark.asyncio
async def test_find_teachers_invalid_type_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MagicMock(spec=UniversitySessionProvider)
    provider.group = "x"
    client = UniversityApiClient(provider)

    async def fake_autocomplete(_value: str) -> dict:
        return {"response": {"groups": [], "rooms": [], "teachers": "bad"}, "error": ""}

    monkeypatch.setattr(client, "autocomplete", fake_autocomplete)
    with pytest.raises(UniversityApiError, match="Invalid teachers format"):
        await client.find_teachers("x")
