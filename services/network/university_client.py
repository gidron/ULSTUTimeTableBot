"""Фасад: авторизованная сессия + методы API для группы."""

from __future__ import annotations

import httpx

from .api_client import UniversityApiClient
from .session_provider import UniversitySessionProvider


class UniversityClient:
    """Фасад: контекстный менеджер с авторизацией и методами API для группы.

    Каждый экземпляр со своей httpx-сессией; после ``async with`` сессия закрывается.
    """

    def __init__(
        self,
        group_name: str,
        *,
        session_provider: UniversitySessionProvider | None = None,
    ) -> None:
        self._group_name = group_name.strip()
        self.session_provider = session_provider or UniversitySessionProvider(
            group=self._group_name
        )

    @property
    def group_name(self) -> str:
        return self._group_name

    async def __aenter__(self) -> "UniversityClient":
        await self.session_provider.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.session_provider.__aexit__(exc_type, exc, tb)

    async def get_session(self) -> httpx.AsyncClient:
        return await self.session_provider.get_authorized_client()

    async def get_session_cookie(self) -> str | None:
        return await self.session_provider.get_time_session_cookie()

    async def get_current_week(self) -> int:
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.get_current_week()

    async def get_timetable(self) -> dict:
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.get_timetable()

    async def get_current_week_and_timetable(self) -> tuple[int, dict]:
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.get_current_week_and_timetable()

    async def group_exists(self):
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.group_exists()

    async def find_groups(self):
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.find_groups(self.session_provider.group)
