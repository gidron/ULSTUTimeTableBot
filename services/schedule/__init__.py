"""Недельное расписание: разбор API, даты, отрисовка PNG, оркестрация `ScheduleService`."""

from __future__ import annotations

from services.schedule.parser import TimetableParseError, TimetableParser

__all__ = [
    "ScheduleService",
    "ScheduleRenderer",
    "TimetableParseError",
    "TimetableParser",
]


def __getattr__(name: str):
    if name == "ScheduleRenderer":
        from services.schedule.renderer import ScheduleRenderer

        return ScheduleRenderer
    if name == "ScheduleService":
        from services.schedule.service import ScheduleService

        return ScheduleService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
