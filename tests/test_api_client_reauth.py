"""Тесты эвристики повторной авторизации API."""

from __future__ import annotations

import httpx

from services.network.api_client import UniversityApiClient


def _response(
    status_code: int = 200,
    *,
    content_type: str | None = "application/json",
    text: str = "{}",
) -> httpx.Response:
    headers = {}
    if content_type is not None:
        headers["Content-Type"] = content_type
    request = httpx.Request("GET", "https://api.example/")
    return httpx.Response(status_code, headers=headers, text=text, request=request)


def test_response_requires_reauth_status_401() -> None:
    r = _response(401, content_type="application/json")
    assert UniversityApiClient._response_requires_reauth(r) is True


def test_response_requires_reauth_status_403() -> None:
    r = _response(403, content_type="application/json")
    assert UniversityApiClient._response_requires_reauth(r) is True


def test_response_requires_reauth_json_ok() -> None:
    r = _response(200, content_type="application/json; charset=utf-8")
    assert UniversityApiClient._response_requires_reauth(r) is False


def test_response_requires_reauth_html_login_page() -> None:
    body = '<html><form action="/auth/login"><input type="password" name="p"></form></html>'
    r = _response(200, content_type="text/html", text=body)
    assert UniversityApiClient._response_requires_reauth(r) is True


def test_response_requires_reauth_html_without_markers() -> None:
    r = _response(200, content_type="text/html", text="<html><body>ok</body></html>")
    assert UniversityApiClient._response_requires_reauth(r) is False
