"""HTTP-клиент УлГТУ: сессия ЛК + запросы к API расписания."""

from __future__ import annotations

import httpx

from .api_client import UniversityApiClient
from .session_provider import (
    UniversitySessionProvider,
    close_shared_session_provider,
    get_shared_session_provider,
)


class UniversityClient:
    """Фасад: запросы API для учебной группы поверх общей сессии time.ulstu.ru."""

    def __init__(
        self,
        group_name: str,
        *,
        session_provider: UniversitySessionProvider | None = None,
    ) -> None:
        self._group_name = group_name.strip()
        self.session_provider = session_provider or get_shared_session_provider()

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
        return await client.get_timetable(self._group_name)

    async def get_current_week_and_timetable(self) -> tuple[int, dict]:
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.get_current_week_and_timetable(self._group_name)

    async def group_exists(self):
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.group_exists(self._group_name)

    async def find_groups(self):
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.find_groups(self._group_name)


__all__ = [
    "UniversityApiClient",
    "UniversityClient",
    "UniversitySessionProvider",
    "close_shared_session_provider",
    "get_shared_session_provider",
]
