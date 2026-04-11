"""Общие фикстуры для unit-тестов."""

from __future__ import annotations

import os

# Модули вроде services.network.api_client вызывают get_settings() при импорте;
# без значений в окружении тесты не соберутся без .env.
_TEST_ENV_DEFAULTS: dict[str, str] = {
    "BOT_TOKEN": "test-bot-token",
    "UNIVERSITY_LOGIN": "u",
    "UNIVERSITY_PASSWORD": "p",
    "LOGIN_URL": "https://example.edu/login",
    "HOME_URL": "https://example.edu/",
    "TIMETABLE_API_URL": "https://example.edu/api/timetable",
    "TIMETABLE_PAGE_URL": "https://example.edu/timetable",
    "CURRENT_WEEK_API_URL": "https://example.edu/api/current-week",
    "AUTOCOMPLETE_API_URL": "https://example.edu/api/autocomplete",
    "BOT_LINK_TEXT": "t.me/test",
    "PG_DATABASE": "testdb",
    "PG_PASSWORD": "test",
    "PG_HOST": "localhost",
    "PG_PORT": "5432",
    "PG_USER": "test",
    "REDIS_HOST": "localhost",
    "REDIS_PORT": "6379",
}
for _key, _val in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _val)

import pytest


@pytest.fixture
def minimal_timetable_payload() -> dict:
    """Минимальный ответ API: две учебные недели с одним днём и пустыми слотами."""
    empty_day = {"day": 0, "lessons": [[] for _ in range(8)]}
    return {
        "response": {
            "weeks": {
                "0": {"days": [empty_day]},
                "1": {"days": [empty_day]},
            }
        }
    }
