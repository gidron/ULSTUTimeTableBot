"""JSON-запросы к API недели и расписания (поверх авторизованной сессии)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.config import get_settings
from .exceptions import UniversityApiError, UniversityAuthError
from .http_retry import request_with_retry
from .session_provider import UniversitySessionProvider

settings = get_settings()
logger = logging.getLogger("client")


class UniversityApiClient:
    """Клиент эндпоинтов current-week, timetable, autocomplete с повторной авторизацией при 401."""

    CURRENT_WEEK_API_URL = settings.current_week_api_url
    TIMETABLE_API_URL = settings.timetable_api_url
    AUTOCOMPLETE_API_URL = settings.autocomplete_api_url

    def __init__(
        self,
        session_provider: UniversitySessionProvider,
    ) -> None:
        self.session_provider = session_provider
        self.group = session_provider.group

        logger.debug("UniversityApiClient initialized | group=%s", self.group)

    async def get_current_week(self) -> int:
        logger.debug("Requesting current week")
        data = await self._request_json(
            "GET",
            self.CURRENT_WEEK_API_URL,
        )

        try:
            week = int(data["response"])
            logger.debug("Current week received | week=%s", week)
            return week
        except (KeyError, TypeError, ValueError) as exc:
            logger.exception("Invalid current-week response")
            raise UniversityApiError("Invalid current-week API response.") from exc

    async def get_timetable(self) -> dict[str, Any]:
        logger.debug("Requesting timetable | group=%s", self.group)
        data = await self._request_json(
            "GET",
            self.TIMETABLE_API_URL,
            params={"filter": self.group},
        )

        logger.debug(
            "Timetable received | keys=%s",
            list(data.keys()) if isinstance(data, dict) else type(data).__name__,
        )
        return data

    async def autocomplete(self, value: str) -> dict[str, Any]:
        logger.debug("Requesting autocomplete | value=%s", value)
        data = await self._request_json(
            "GET",
            self.AUTOCOMPLETE_API_URL,
            params={"value": value},
        )
        logger.debug("Autocomplete response received")
        return data

    async def find_groups(self, value: str) -> list[str]:
        logger.debug("Finding groups via autocomplete | value=%s", value)
        data = await self.autocomplete(value)

        try:
            groups = data["response"]["groups"]
        except (KeyError, TypeError) as exc:
            logger.exception("Invalid autocomplete response structure")
            raise UniversityApiError("Invalid autocomplete API response.") from exc

        if not isinstance(groups, list):
            logger.error("Autocomplete groups is not a list")
            raise UniversityApiError("Invalid groups format in autocomplete response.")

        result = [str(g).strip() for g in groups if str(g).strip()]
        logger.debug("Groups found | count=%s | groups=%s", len(result), result)
        return result

    async def group_exists(self) -> bool:
        normalized_group = self.group.strip()
        logger.debug("Checking group existence | group_name=%s", normalized_group)

        groups = await self.find_groups(normalized_group)
        exists = normalized_group in groups

        logger.debug(
            "Group existence result | group_name=%s | exists=%s | matched_groups=%s",
            normalized_group,
            exists,
            groups,
        )
        return exists

    async def get_current_week_and_timetable(self) -> tuple[int, dict[str, Any]]:
        logger.info("Requesting current week and timetable")
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

        client = await self.session_provider.get_authorized_client()

        response = await request_with_retry(
            client,
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
                    "Session expired and re-authentication did not help."
                )

            await self.session_provider.refresh_authorization()
            client = await self.session_provider.get_authorized_client()

            response = await request_with_retry(
                client,
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
            logger.error(
                "API request failed | url=%s | status_code=%s",
                url,
                response.status_code,
            )
            raise UniversityApiError(
                f"API request failed for {url}. HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("API returned invalid JSON | url=%s", url)
            raise UniversityApiError(f"API {url} returned non-JSON body.") from exc

        error_text = data.get("error")
        if error_text:
            logger.error(
                "API returned error field | url=%s | error=%s", url, error_text
            )
            raise UniversityApiError(f"API returned error: {error_text}")

        logger.debug("API JSON parsed successfully | url=%s", url)
        return data

    @staticmethod
    def _response_requires_reauth(response: httpx.Response) -> bool:
        if response.status_code in {401, 403}:
            logger.debug(
                "Re-auth required because of status code %s", response.status_code
            )
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
        result = "html" in content_type and any(
            marker in text for marker in auth_markers
        )
        logger.debug(
            "Re-auth check by response body | content_type=%s | result=%s",
            content_type,
            result,
        )
        return result
