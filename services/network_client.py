from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import get_settings

settings = get_settings()
logger = logging.getLogger("client")


class UniversityClientError(Exception):
    pass


class UniversityAuthError(UniversityClientError):
    pass


class UniversityApiError(UniversityClientError):
    pass


class UniversityClient:
    LOGIN_URL = settings.login_url
    HOME_URL = settings.home_url
    TIMETABLE_PAGE_URL = settings.timetable_page_url
    CURRENT_WEEK_API_URL = settings.current_week_api_url
    TIMETABLE_API_URL = settings.timetable_api_url

    def __init__(
            self,
            login: str = settings.university_login,
            password: str = settings.university_password,
            group: str = settings.group_name,
            timeout: float = settings.request_timeout,
    ) -> None:
        self.login = login
        self.password = password
        self.group = group
        self.timeout = timeout
        self._authorized = False

        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) "
                    "Gecko/20100101 Firefox/148.0"
                ),
                "Accept-Language": "ru,en-US;q=0.9,en;q=0.8",
                "DNT": "1",
            },
        )

        logger.debug(
            "UniversityClient initialized | login=%s | group=%s | timeout=%s",
            self.login,
            self.group,
            self.timeout,
        )

    async def __aenter__(self) -> "UniversityClient":
        logger.debug("Entering UniversityClient context")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        logger.debug(
            "Exiting UniversityClient context | exc_type=%s | exc=%s",
            exc_type,
            exc,
        )
        await self.close()

    async def close(self) -> None:
        logger.debug("Closing HTTP client")
        await self.client.aclose()

    async def ensure_authorized(self) -> None:
        has_session = self._has_time_session()
        logger.debug(
            "Checking authorization | authorized=%s | has_time_session=%s",
            self._authorized,
            has_session,
        )

        if self._authorized and has_session:
            logger.debug("Authorization is still valid")
            return

        logger.info("Authorization required")
        await self.authorize()

    async def authorize(self) -> None:
        logger.info("Starting authorization flow")
        self._authorized = False

        self.client.cookies.clear()
        logger.debug("Cookie jar cleared")

        logger.debug("Sending login request | url=%s | login=%s", self.LOGIN_URL, self.login)
        login_response = await self.client.post(
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
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "*/*;q=0.8"
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
                f"Не удалось выполнить вход в ЛК. HTTP {login_response.status_code}"
            )

        logger.debug("Opening home page | url=%s", self.HOME_URL)
        home_response = await self.client.get(
            self.HOME_URL,
            headers={
                "Referer": "https://lk.ulstu.ru/?q=auth/login&r=q%3Dhome",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
            },
        )

        logger.debug(
            "Home page response received | status_code=%s | final_url=%s",
            home_response.status_code,
            str(home_response.url),
        )

        if home_response.status_code != 200:
            logger.error("Home page open failed | status_code=%s", home_response.status_code)
            raise UniversityAuthError(
                f"Не удалось открыть главную страницу ЛК. HTTP {home_response.status_code}"
            )

        looks_logged_in = self._looks_like_logged_in_home(home_response.text)
        logger.debug("Logged-in home page detected=%s", looks_logged_in)

        if not looks_logged_in:
            logger.error("Authorization failed: home page does not look authenticated")
            raise UniversityAuthError(
                "Похоже, авторизация не удалась: главная страница ЛК "
                "не выглядит как страница авторизованного пользователя."
            )

        logger.debug(
            "Opening timetable page to obtain session cookie | url=%s | group=%s",
            self.TIMETABLE_PAGE_URL,
            self.group,
        )
        timetable_page_response = await self.client.get(
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
                f"Не удалось открыть страницу расписания. "
                f"HTTP {timetable_page_response.status_code}"
            )

        has_session = self._has_time_session()
        logger.debug("Session cookie presence after timetable page open=%s", has_session)

        if not has_session:
            logger.error("No time.ulstu.ru session cookie after timetable page open")
            raise UniversityAuthError(
                "После перехода на time.ulstu.ru не появилась cookie session."
            )

        self._authorized = True
        logger.info("Authorization flow completed successfully")

    async def get_current_week(self) -> int:
        logger.debug("Requesting current week")
        data = await self._request_json(
            "GET",
            self.CURRENT_WEEK_API_URL,
            retry_on_auth=True,
        )

        try:
            week = int(data["response"])
            logger.debug("Current week received | week=%s", week)
            return week
        except (KeyError, TypeError, ValueError) as exc:
            logger.exception("Invalid current-week response")
            raise UniversityApiError("Некорректный ответ current-week.") from exc

    async def get_timetable(self) -> dict[str, Any]:
        logger.debug("Requesting timetable | group=%s", self.group)
        data = await self._request_json(
            "GET",
            self.TIMETABLE_API_URL,
            params={"filter": self.group},
            retry_on_auth=True,
        )

        logger.debug(
            "Timetable received | keys=%s",
            list(data.keys()) if isinstance(data, dict) else type(data).__name__,
        )
        return data

    async def get_current_week_and_timetable(self) -> tuple[int, dict[str, Any]]:
        logger.info("Requesting current week and timetable")
        await self.ensure_authorized()
        current_week = await self.get_current_week()
        timetable = await self.get_timetable()
        logger.info("Current week and timetable received successfully")
        return current_week, timetable

    async def _request_json(
            self,
            method: str,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            retry_on_auth: bool = True,
    ) -> dict[str, Any]:
        logger.debug(
            "Preparing API request | method=%s | url=%s | params=%s | retry_on_auth=%s",
            method,
            url,
            params,
            retry_on_auth,
        )

        await self.ensure_authorized()

        response = await self.client.request(
            method,
            url,
            params=params,
            headers={
                "Accept": "application/json, text/plain, */*",
            },
        )

        logger.debug(
            "API response received | url=%s | status_code=%s | content_type=%s",
            url,
            response.status_code,
            response.headers.get("Content-Type"),
        )

        if self._response_requires_reauth(response):
            logger.info("API response requires re-authentication | url=%s", url)

            if not retry_on_auth:
                logger.error("Re-authentication disabled and required | url=%s", url)
                raise UniversityAuthError(
                    "Сессия истекла и повторная авторизация не помогла."
                )

            await self.authorize()

            response = await self.client.request(
                method,
                url,
                params=params,
                headers={
                    "Accept": "application/json, text/plain, */*",
                },
            )

            logger.debug(
                "API response after re-auth received | url=%s | status_code=%s",
                url,
                response.status_code,
            )

        if response.status_code != 200:
            logger.error("API request failed | url=%s | status_code=%s", url, response.status_code)
            raise UniversityApiError(
                f"Ошибка запроса к API {url}. HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("API returned invalid JSON | url=%s", url)
            raise UniversityApiError(f"API {url} вернул не JSON.") from exc

        error_text = data.get("error")
        if error_text:
            logger.error("API returned error field | url=%s | error=%s", url, error_text)
            raise UniversityApiError(f"API вернул ошибку: {error_text}")

        logger.debug("API JSON parsed successfully | url=%s", url)
        return data

    def _has_time_session(self) -> bool:
        for cookie in self.client.cookies.jar:
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

    @staticmethod
    def _response_requires_reauth(response: httpx.Response) -> bool:
        if response.status_code in {401, 403}:
            logger.debug("Re-auth required because of status code %s", response.status_code)
            return True

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            logger.debug("JSON response does not require re-auth by content type")
            return False

        text = response.text.lower()
        auth_markers = (
            "auth/login",
            "form",
            "password",
        )
        result = "html" in content_type and any(marker in text for marker in auth_markers)
        logger.debug(
            "Re-auth check by response body | content_type=%s | result=%s",
            content_type,
            result,
        )
        return result
