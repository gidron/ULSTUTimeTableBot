"""Фасад: авторизованная сессия + методы API для группы."""

from __future__ import annotations

import httpx

from .account_selector import get_university_account_selector
from .api_client import UniversityApiClient
from .session_provider import UniversitySessionProvider


class UniversityClient:
    """Фасад: контекстный менеджер с авторизацией и методами API для группы.

    Каждый экземпляр со своей httpx-сессией; после ``async with`` сессия закрывается.
    Учётная запись выбирается round-robin при входе в контекст (если не переданы явно).
    """

    def __init__(
        self,
        group_name: str,
        *,
        session_provider: UniversitySessionProvider | None = None,
        login: str | None = None,
        password: str | None = None,
    ) -> None:
        self._group_name = group_name.strip()
        self._preset_session_provider = session_provider
        self._explicit_login = login
        self._explicit_password = password
        self._session_provider: UniversitySessionProvider | None = session_provider

    @property
    def group_name(self) -> str:
        return self._group_name

    @property
    def session_provider(self) -> UniversitySessionProvider:
        if self._session_provider is None:
            raise RuntimeError(
                "UniversityClient must be used with async with before accessing session_provider"
            )
        return self._session_provider

    async def __aenter__(self) -> "UniversityClient":
        if self._session_provider is None:
            if self._preset_session_provider is not None:
                self._session_provider = self._preset_session_provider
            elif self._explicit_login is not None:
                self._session_provider = UniversitySessionProvider(
                    group=self._group_name,
                    login=self._explicit_login,
                    password=self._explicit_password or "",
                )
            else:
                cred_login, cred_password = (
                    await get_university_account_selector().pick()
                )
                self._session_provider = UniversitySessionProvider(
                    group=self._group_name,
                    login=cred_login,
                    password=cred_password,
                )
        await self._session_provider.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session_provider is not None:
            await self._session_provider.__aexit__(exc_type, exc, tb)
        self._session_provider = None

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

    async def find_teachers(self):
        client = UniversityApiClient(session_provider=self.session_provider)
        return await client.find_teachers(self.session_provider.group)
