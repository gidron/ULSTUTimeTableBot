"""Расчёт дат для строк расписания и подсветки «текущего» дня на картинке."""

from __future__ import annotations

from datetime import date, datetime, timedelta


def build_week_date_range(week_monday: date) -> str:
    """Строка диапазона недели «пн–сб» в формате ДД.ММ - ДД.ММ."""
    week_saturday = week_monday + timedelta(days=5)
    return f"{week_monday.strftime('%d.%m')} - {week_saturday.strftime('%d.%m')}"


def compute_highlight_day_index(
    current_week_number: int | None,
    selected_week_number: int,
    *,
    reference: datetime | None = None,
) -> int | None:
    """Индекс дня (0–5) для подсветки, если на экране выбрана именно текущая неделя API."""
    if current_week_number is None:
        return None
    if current_week_number != selected_week_number:
        return None
    ref = reference or datetime.now()
    weekday = ref.weekday()
    return weekday if 0 <= weekday <= 5 else None


def attach_dates_to_week_days(
    normalized_payload: dict,
    current_week_number: int | None,
    selected_display_week_number: int,
    *,
    today: date | None = None,
) -> None:
    """Проставляет поле date у дней и week_date_range в payload; без номера текущей недели — ничего."""
    if current_week_number is None:
        return

    ref_date = today or datetime.now().date()
    current_monday = ref_date - timedelta(days=ref_date.weekday())
    week_offset = selected_display_week_number - current_week_number
    selected_monday = current_monday + timedelta(days=week_offset * 7)

    for day_payload in normalized_payload.get("days", []):
        day_index = day_payload.get("day_index")
        if day_index is None:
            continue
        day_date = selected_monday + timedelta(days=day_index)
        day_payload["date"] = day_date.strftime("%d.%m")

    normalized_payload["week_date_range"] = build_week_date_range(selected_monday)
