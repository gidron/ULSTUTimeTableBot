"""Тесты расчёта дат недели и подсветки дня."""

from __future__ import annotations

from datetime import date, datetime

from services.schedule.week_dates import (
    attach_dates_to_week_days,
    build_week_date_range,
    compute_highlight_day_index,
    day_calendar_date,
)


def test_build_week_date_range() -> None:
    monday = date(2026, 4, 6)
    assert build_week_date_range(monday) == "06.04 - 11.04"


def test_compute_highlight_day_index_same_week_and_monday() -> None:
    ref = datetime(2026, 4, 6, 12, 0, 0)
    assert compute_highlight_day_index(10, 10, reference=ref) == 0


def test_compute_highlight_day_index_wrong_week() -> None:
    ref = datetime(2026, 4, 8, 12, 0, 0)
    assert compute_highlight_day_index(10, 11, reference=ref) is None


def test_compute_highlight_day_index_no_current_week() -> None:
    assert compute_highlight_day_index(None, 1) is None


def test_compute_highlight_day_index_sunday_not_highlighted() -> None:
    ref = datetime(2026, 4, 12, 12, 0, 0)
    assert compute_highlight_day_index(5, 5, reference=ref) is None


def test_day_calendar_date_offset() -> None:
    today = date(2026, 4, 8)
    assert day_calendar_date(0, 10, 9, today=today) == date(2026, 4, 13)
    assert day_calendar_date(2, 10, 10, today=today) == date(2026, 4, 8)


def test_attach_dates_to_week_days_skips_without_current() -> None:
    payload = {"days": [{"day_index": 0, "slots": []}]}
    attach_dates_to_week_days(payload, None, 1)
    assert "week_date_range" not in payload
    assert "date" not in payload["days"][0]


def test_attach_dates_to_week_days_sets_dates() -> None:
    payload = {
        "days": [
            {"day_index": 0, "slots": []},
            {"day_index": 2, "slots": []},
        ]
    }
    today = date(2026, 4, 8)
    attach_dates_to_week_days(payload, 10, 10, today=today)
    assert payload["week_date_range"] == "06.04 - 11.04"
    assert payload["days"][0]["date"] == "06.04"
    assert payload["days"][1]["date"] == "08.04"


def test_attach_dates_to_week_days_semester_start_no_offset() -> None:
    """При current-week=0 даты текущей недели без смещения +7."""
    payload = {"days": [{"day_index": 0, "slots": []}]}
    today = date(2026, 9, 1)
    attach_dates_to_week_days(payload, 0, 0, today=today)
    assert payload["week_date_range"] == "31.08 - 05.09"
    assert payload["days"][0]["date"] == "31.08"
