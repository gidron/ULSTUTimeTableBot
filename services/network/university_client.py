"""Фасад: авторизованная сессия + методы API для группы."""

from __future__ import annotations

import logging

import httpx

from core.config import get_settings

from .account_selector import get_university_account_selector
from .api_client import UniversityApiClient
from .exceptions import UniversityAuthError
from .session_provider import UniversitySessionProvider

logger = logging.getLogger("client")


class UniversityClient:
    """Фасад: контекстный менеджер с авторизацией и методами API для группы.

    Каждый экземпляр со своей httpx-сессией; после ``async with`` сессия закрывается.
    Учётная запись выбирается round-robin при входе в контекст (если не переданы явно).
    При ошибке входа в ЛК перебираются остальные учётки из пула (не более одного раза на каждую).
    После успешного входа при сбое повторной авторизации (например после 401 API) снова
    перебираются остальные учётки из пула, пока не сработает вход или не кончатся варианты.
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
        failover_session_already_entered = False
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
                pool = get_settings().university_credentials_pool()
                attempts = len(pool)
                last_auth_error: UniversityAuthError | None = None
                for attempt in range(attempts):
                    (
                        cred_login,
                        cred_password,
                    ) = await get_university_account_selector().pick()
                    sp = UniversitySessionProvider(
                        group=self._group_name,
                        login=cred_login,
                        password=cred_password,
                        enable_account_failover=True,
                    )
                    await sp.__aenter__()
                    try:
                        await sp.get_authorized_client()
                    except UniversityAuthError as exc:
                        last_auth_error = exc
                        logger.warning(
                            "University auth failed | lk_login=%s | attempt=%s/%s | %s",
                            cred_login,
                            attempt + 1,
                            attempts,
                            exc,
                        )
                        await sp.__aexit__(None, None, None)
                        continue
                    self._session_provider = sp
                    failover_session_already_entered = True
                    if attempt > 0:
                        logger.info(
                            "University auth succeeded after failover | lk_login=%s",
                            cred_login,
                        )
                    break
                else:
                    assert last_auth_error is not None
                    raise last_auth_error
        if not failover_session_already_entered:
            assert self._session_provider is not None
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
