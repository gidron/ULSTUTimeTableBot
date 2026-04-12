"""Режим отрисовки PNG расписания: дни строками (horizontal) или столбцами (vertical)."""

from __future__ import annotations

from enum import Enum, unique


@unique
class ScheduleLayout(str, Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


def parse_schedule_layout(value: str | None) -> ScheduleLayout:
    """Безопасное значение из БД: при неизвестной строке — horizontal."""
    if not value:
        return ScheduleLayout.HORIZONTAL
    try:
        return ScheduleLayout(value)
    except ValueError:
        return ScheduleLayout.HORIZONTAL
