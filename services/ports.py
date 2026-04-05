"""Протоколы зависимостей для сервиса расписания (подстановка в тестах и DI)."""

from __future__ import annotations

from typing import Protocol


class TimetableSource(Protocol):
    """Источник сырых данных расписания с университетского API."""

    async def __aenter__(self) -> TimetableSource: ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def get_current_week_and_timetable(self) -> tuple[int | None, dict]: ...


class ScheduleImageRenderer(Protocol):
    """Рендер нормализованного расписания в изображение (PNG байты)."""

    def render(self, week_payload: dict) -> bytes: ...
