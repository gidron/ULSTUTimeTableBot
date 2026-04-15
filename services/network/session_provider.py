"""Управление httpx-сессией: логин в ЛК, cookie для time.ulstu.ru."""

from __future__ import annotations

import asyncio
import logging

import httpx

from core.config import get_settings
from .exceptions import UniversityAuthError
from .http_retry import request_with_retry

settings = get_settings()
logger = logging.getLogger("client")


class UniversitySessionProvider:
    """Контекстный менеджер: при необходимости выполняет цикл логина и открытия страниц.

    Один экземпляр на один цикл ``async with UniversityClient`` — клиент закрывается при выходе.
    """

    LOGIN_URL = settings.login_url
    HOME_URL = settings.home_url
    TIMETABLE_PAGE_URL = settings.timetable_page_url

    def __init__(
        self,
        group: str,
        login: str = settings.university_login,
        password: str = settings.university_password,
        timeout: float = settings.request_timeout,
    ) -> None:
        self.login = login
        self.password = password
        self.group = group
        self.timeout = timeout

        self._client: httpx.AsyncClient | None = None
        self._authorized = False
        self._auth_lock = asyncio.Lock()

        logger.debug(
            "UniversitySessionProvider initialized | login=%s | group=%s | timeout=%s",
            self.login,
            self.group,
            self.timeout,
        )

    async def __aenter__(self) -> "UniversitySessionProvider":
        logger.debug("Entering UniversitySessionProvider context")
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.debug(
            "Exiting UniversitySessionProvider context | exc_type=%s | exc=%s",
            exc_type,
            exc,
        )
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            logger.debug("Closing session provider HTTP client")
            await self._client.aclose()
            self._client = None
            self._authorized = False

    async def get_authorized_client(self) -> httpx.AsyncClient:
        await self._ensure_client()

        if self._authorized and self._has_time_session():
            logger.debug("Reusing existing authorized session")
            return self._client  # type: ignore[return-value]

        logger.info("Authorized session required, starting authorization")
        async with self._auth_lock:
            if self._authorized and self._has_time_session():
                logger.debug("Reusing existing authorized session after lock wait")
                return self._client  # type: ignore[return-value]
            await self._do_authorize()
            return self._client  # type: ignore[return-value]

    async def get_time_session_cookie(self) -> str | None:
        client = await self.get_authorized_client()

        for cookie in client.cookies.jar:
            if cookie.name == "session" and "time.ulstu.ru" in cookie.domain:
                logger.debug("Returning time.ulstu.ru session cookie")
                return cookie.value

        logger.debug("time.ulstu.ru session cookie not found")
        return None

    async def refresh_authorization(self) -> None:
        logger.info("Refreshing authorization")
        await self._ensure_client()
        async with self._auth_lock:
            await self._do_authorize()

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            verify=settings.verify_ssl,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) "
                    "Gecko/20100101 Firefox/148.0"
                ),
                "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
                "DNT": "1",
            },
        )
        logger.debug("HTTP client created")

    async def _do_authorize(self) -> None:
        assert self._client is not None

        logger.info("Starting authorization flow")
        self._authorized = False

        self._client.cookies.clear()
        logger.debug("Cookie jar cleared")

        login_response = await request_with_retry(
            self._client,
            "POST",
            self.LOGIN_URL,
            data={
                "login": self.login,
                "password": self.password,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://lk.ulstu.ru",
                "Referer": "https://lk.ulstu.ru/?q=auth/login&r=q%3Dhome",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
            },
        )

        logger.debug(
            "Login response received | status_code=%s | final_url=%s",
            login_response.status_code,
            str(login_response.url),
        )

        if login_response.status_code != 200:
            logger.error("Login failed | status_code=%s", login_response.status_code)
            raise UniversityAuthError(
                f"University login failed. HTTP {login_response.status_code}"
            )

        home_response = await request_with_retry(
            self._client,
            "GET",
            self.HOME_URL,
            headers={
                "Referer": "https://lk.ulstu.ru/?q=auth/login&r=q%3Dhome",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
            },
        )

        logger.debug(
            "Home page response received | status_code=%s | final_url=%s",
            home_response.status_code,
            str(home_response.url),
        )

        if home_response.status_code != 200:
            logger.error(
                "Home page open failed | status_code=%s", home_response.status_code
            )
            raise UniversityAuthError(
                f"Failed to open university home page. HTTP {home_response.status_code}"
            )

        if not self._looks_like_logged_in_home(home_response.text):
            logger.error("Authorization failed: home page is not authenticated")
            raise UniversityAuthError(
                "Authorization failed: home page does not look like an authenticated session."
            )

        timetable_page_response = await request_with_retry(
            self._client,
            "GET",
            self.TIMETABLE_PAGE_URL,
            params={"filter": self.group},
            headers={
                "Referer": "https://lk.ulstu.ru/?q=home",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        logger.debug(
            "Timetable page response received | status_code=%s | final_url=%s",
            timetable_page_response.status_code,
            str(timetable_page_response.url),
        )

        if timetable_page_response.status_code != 200:
            logger.error(
                "Timetable page open failed | status_code=%s",
                timetable_page_response.status_code,
            )
            raise UniversityAuthError(
                f"Failed to open timetable page. HTTP {timetable_page_response.status_code}"
            )

        if not self._has_time_session():
            logger.error("No time.ulstu.ru session cookie after timetable page open")
            raise UniversityAuthError(
                "No session cookie appeared after navigating to time.ulstu.ru."
            )

        self._authorized = True
        logger.info(
            "Authorization completed successfully | lk_login=%s | group=%s",
            self.login,
            self.group,
        )

    def _has_time_session(self) -> bool:
        if self._client is None:
            return False

        for cookie in self._client.cookies.jar:
            logger.debug(
                "Inspecting cookie | name=%s | domain=%s",
                cookie.name,
                cookie.domain,
            )
            if cookie.name == "session" and "time.ulstu.ru" in cookie.domain:
                logger.debug("time.ulstu.ru session cookie found")
                return True

        logger.debug("time.ulstu.ru session cookie not found")
        return False

    @staticmethod
    def _looks_like_logged_in_home(html: str) -> bool:
        markers = (
            "Личный кабинет УлГТУ",
            "Профиль",
            "Выход",
        )
        result = all(marker in html for marker in markers)
        logger.debug("Home page marker check result=%s", result)
        return result
