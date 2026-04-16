"""Тесты расписания на день по дате и двухнедельному шаблону."""

from __future__ import annotations

from datetime import date

import pytest

from services.schedule.day_for_date import (
    build_day_schedule_snapshot,
    parse_dm_text,
    resolve_semester_calendar_date,
)
from services.schedule.parser import TimetableParseError


def test_parse_dm_text_ok() -> None:
    assert parse_dm_text("15.02") == (15, 2)
    assert parse_dm_text("  5.12 ") == (5, 12)


def test_parse_dm_text_rejects() -> None:
    assert parse_dm_text("15.02.2026") is None
    assert parse_dm_text("15/02") is None
    assert parse_dm_text("foo") is None


def test_resolve_semester_spring_same_year_past() -> None:
    """16.04 → ввод 14.04 — тот же год, день в прошлом внутри семестра."""
    today = date(2026, 4, 16)
    assert resolve_semester_calendar_date(14, 4, today) == date(2026, 4, 14)


def test_resolve_semester_spring_future_in_same_semester() -> None:
    today = date(2026, 4, 10)
    assert resolve_semester_calendar_date(20, 4, today) == date(2026, 4, 20)


def test_resolve_semester_spring_rejects_fall_month() -> None:
    today = date(2026, 4, 16)
    with pytest.raises(ValueError, match="период"):
        resolve_semester_calendar_date(14, 9, today)


def test_resolve_semester_fall_rejects_spring_month() -> None:
    today = date(2026, 10, 15)
    with pytest.raises(ValueError, match="период"):
        resolve_semester_calendar_date(14, 4, today)


def test_resolve_semester_january_uses_spring_window() -> None:
    today = date(2026, 1, 10)
    assert resolve_semester_calendar_date(14, 4, today) == date(2026, 4, 14)


def test_resolve_semester_july_uses_fall_window() -> None:
    today = date(2026, 7, 15)
    assert resolve_semester_calendar_date(20, 9, today) == date(2026, 9, 20)


def test_resolve_semester_invalid_day() -> None:
    with pytest.raises(ValueError, match="Некорректная"):
        resolve_semester_calendar_date(31, 2, date(2026, 4, 10))


def _minimal_weeks_payload() -> dict:
    """При api_current_week=3: current_key=\"2\", next_key=\"3\" (см. TimetableParser.pick_week)."""
    monday_lesson_a = {
        "day": 0,
        "lessons": [
            [{"nameOfLesson": "A", "teacher": "T", "room": "1"}],
        ]
        + [[] for _ in range(7)],
    }
    monday_lesson_b = {
        "day": 0,
        "lessons": [
            [{"nameOfLesson": "B", "teacher": "T", "room": "2"}],
        ]
        + [[] for _ in range(7)],
    }
    return {
        "response": {
            "weeks": {
                "2": {"days": [monday_lesson_a]},
                "3": {"days": [monday_lesson_b]},
            }
        }
    }


def test_build_snapshot_sunday() -> None:
    payload = _minimal_weeks_payload()
    out = build_day_schedule_snapshot(
        date(2026, 4, 12),
        api_current_week=3,
        payload=payload,
        group_name="G",
        today=date(2026, 4, 10),
    )
    assert out == "sunday"


def test_build_snapshot_parity_current_week() -> None:
    """Та же учебная неделя, что и «текущая» (чётность 0) → шаблон недели «2», пн → предмет A."""
    from services.schedule.day_for_date import DayScheduleSnapshot

    payload = _minimal_weeks_payload()
    out = build_day_schedule_snapshot(
        date(2026, 4, 6),
        api_current_week=3,
        payload=payload,
        group_name="G",
        today=date(2026, 4, 6),
    )
    assert isinstance(out, DayScheduleSnapshot)
    assert "A" in out.slots[0]


def test_build_snapshot_next_week_parity() -> None:
    """Следующая учебная неделя (чётность 1) → шаблон недели «3», пн → предмет B."""
    from services.schedule.day_for_date import DayScheduleSnapshot

    payload = _minimal_weeks_payload()
    out = build_day_schedule_snapshot(
        date(2026, 4, 13),
        api_current_week=3,
        payload=payload,
        group_name="G",
        today=date(2026, 4, 6),
    )
    assert isinstance(out, DayScheduleSnapshot)
    assert "B" in out.slots[0]


def test_build_snapshot_missing_next_raises() -> None:
    payload = {"response": {"weeks": {"2": {"days": []}}}}
    with pytest.raises(TimetableParseError):
        build_day_schedule_snapshot(
            date(2026, 4, 13),
            api_current_week=3,
            payload=payload,
            group_name="G",
            today=date(2026, 4, 6),
        )


def test_format_day_schedule_has_header_and_disclaimer() -> None:
    from services.schedule.day_for_date import (
        DayScheduleSnapshot,
        format_day_schedule_html,
    )

    snap = DayScheduleSnapshot(
        group_name="УИДбд-21",
        slots=[""] * 8,
        day_index=0,
        cell_date_str="14.04",
        target_date=date(2026, 4, 14),
    )
    html = format_day_schedule_html(snap)
    assert "Расписание на день" in html
    assert "Ориентировочно" in html
    assert "УИДбд-21" in html
