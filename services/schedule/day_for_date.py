"""Расписание на один календарный день по шаблону двух недель из API."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from core.config import get_settings
from services.schedule.constants import PAIR_HEADERS, PAIR_TIMES, WEEKDAY_NAMES
from services.schedule.parser import TimetableParser
from services.schedule.week_dates import attach_dates_to_week_days

DATE_DM_FULLMATCH = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\s*$")


@dataclass(frozen=True)
class DayScheduleSnapshot:
    """Снимок одного дня: слоты как в PNG, дата и группа."""

    group_name: str
    slots: list[str]
    day_index: int
    cell_date_str: str
    target_date: date


def schedule_today() -> date:
    """Сегодняшняя дата в `schedule_timezone` или локальная календарная."""
    tz = get_settings().schedule_timezone
    if tz:
        return datetime.now(ZoneInfo(tz)).date()
    return date.today()


def parse_dm_text(text: str) -> tuple[int, int] | None:
    """Разбор строки целиком «ДД.ММ» → (день, месяц) или None."""
    m = DATE_DM_FULLMATCH.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _semester_window_for_today(today: date) -> tuple[date, date]:
    """Границы учебного периода для разрешения «ДД.ММ» без года.

    Весна: 1 февраля — 30 июня. Осень: 1 сентября — 31 декабря.
    Январь → ближайший весенний семестр того же года; июль–август → ближайшая осень того же года.
    """
    m, y = today.month, today.year
    if m in (9, 10, 11, 12):
        return date(y, 9, 1), date(y, 12, 31)
    if m in (2, 3, 4, 5, 6):
        return date(y, 2, 1), date(y, 6, 30)
    if m == 1:
        return date(y, 2, 1), date(y, 6, 30)
    # Июль, август — до начала осеннего семестра
    return date(y, 9, 1), date(y, 12, 31)


def is_date_in_semester_window(candidate: date, today: date) -> bool:
    """Попадает ли календарная дата в учебный период, соответствующий ``today``."""
    window_start, window_end = _semester_window_for_today(today)
    return window_start <= candidate <= window_end


def two_iso_weeks_inclusive_range(anchor: date) -> tuple[date, date]:
    """Понедельник недели ``anchor`` и воскресенье через две недели (14 дней)."""
    monday = anchor - timedelta(days=anchor.weekday())
    end = monday + timedelta(days=13)
    return monday, end


def dates_two_iso_weeks_intersect_semester(anchor: date, ref_today: date) -> list[date]:
    """Все календарные дни двух ISO-недель вокруг ``anchor``, ограниченные семестром."""
    start, end = two_iso_weeks_inclusive_range(anchor)
    out: list[date] = []
    d = start
    while d <= end:
        if is_date_in_semester_window(d, ref_today):
            out.append(d)
        d += timedelta(days=1)
    return out


def resolve_semester_calendar_date(day: int, month: int, today: date) -> date:
    """Дата в календаре ``today.year`` в пределах семестра, который соответствует ``today``.

    Можно выбрать день в прошлом внутри того же семестра (например сегодня 16.04, ввод 14.04).
    """
    window_start, window_end = _semester_window_for_today(today)
    if window_start.month == 2:
        allowed_months = frozenset({2, 3, 4, 5, 6})
        period_name = "весеннего семестра (1 февраля — 30 июня)"
    else:
        allowed_months = frozenset({9, 10, 11, 12})
        period_name = "осеннего семестра (1 сентября — 31 декабря)"

    if month not in allowed_months:
        raise ValueError(
            f"Сейчас учитывается период {period_name}. "
            "Укажи дату в месяцах этого семестра."
        )

    try:
        candidate = date(today.year, month, day)
    except ValueError as exc:
        raise ValueError("Некорректная дата (такого дня в месяце нет).") from exc

    if candidate < window_start or candidate > window_end:
        raise ValueError(f"Дата должна попадать в границы {period_name}.")
    return candidate


def build_day_schedule_snapshot(
    target_date: date,
    *,
    api_current_week: int,
    payload: dict,
    group_name: str,
    today: date,
) -> DayScheduleSnapshot | Literal["sunday"]:
    """Собирает слоты дня; для воскресенья возвращает ``\"sunday\"``."""
    wd = target_date.weekday()
    if wd == 6:
        return "sunday"

    target_monday = target_date - timedelta(days=wd)
    today_monday = today - timedelta(days=today.weekday())
    week_offset = (target_monday - today_monday).days // 7
    selected_display_week_number = api_current_week + week_offset

    delta = selected_display_week_number - api_current_week
    week_kind = "current" if delta % 2 == 0 else "next"

    _week_key, week_data = TimetableParser.pick_week(
        payload, week_kind, api_current_week
    )

    normalized = TimetableParser.normalize_week(
        str(selected_display_week_number),
        week_data,
        group_name=group_name,
        highlight_day_index=None,
    )
    attach_dates_to_week_days(
        normalized,
        api_current_week,
        selected_display_week_number,
        today=today,
    )

    day_payload = normalized["days"][wd]
    slots = day_payload["slots"]
    cell_date = day_payload.get("date", target_date.strftime("%d.%m"))

    return DayScheduleSnapshot(
        group_name=group_name,
        slots=slots,
        day_index=wd,
        cell_date_str=cell_date,
        target_date=target_date,
    )


def _pair_time_display(slot_index: int) -> str:
    if slot_index < 0 or slot_index >= len(PAIR_TIMES):
        return ""
    return PAIR_TIMES[slot_index].replace("-", "–", 1)


def _pair_label(slot_index: int) -> str:
    if 0 <= slot_index < len(PAIR_HEADERS):
        return f"{PAIR_HEADERS[slot_index]} пара"
    return f"{slot_index + 1}-я пара"


def _escape_slot_body(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "<i>Окно</i>"
    # В Telegram HTML тег <br> не поддерживается — переносы через \n.
    return html.escape(text)


def format_sunday_off_html(group_name: str, target_date: date) -> str:
    """Тот же каркас, что у расписания на день, но день — вс, тело «Выходной»."""
    full_date = target_date.strftime("%d.%m.%Y")
    gn = html.escape(group_name)
    return "\n".join(
        [
            "📅 <b>Расписание на день</b>",
            "",
            "<i>Ориентировочно: на сайте вуза доступны две учебные недели; бот "
            "продолжает этот шаблон по кругу (чередование «текущая / следующая» неделя). "
            "Это не официальный документ — возможны замены, переносы и изменения. "
            "Сверяйся с актуальным расписанием на сайте.</i>",
            "",
            f"📚 Группа: <b>{gn}</b>",
            f"🗓 Вс · {full_date}",
            "",
            "· · ·",
            "",
            "Выходной.",
        ]
    )


def format_day_schedule_html(snapshot: DayScheduleSnapshot) -> str:
    """HTML-сообщение: шапка, дисклеймер, затем пары."""
    wd_label = (
        WEEKDAY_NAMES[snapshot.day_index]
        if snapshot.day_index < len(WEEKDAY_NAMES)
        else str(snapshot.day_index)
    )
    full_date = snapshot.target_date.strftime("%d.%m.%Y")
    gn = html.escape(snapshot.group_name)
    lines: list[str] = [
        "📅 <b>Расписание на день</b>",
        "",
        "<i>Ориентировочно: на сайте вуза доступны две учебные недели; бот "
        "продолжает этот шаблон по кругу (чередование «текущая / следующая» неделя). "
        "Это не официальный документ — возможны замены, переносы и изменения. "
        "Сверяйся с актуальным расписанием на сайте.</i>",
        "",
        f"📚 Группа: <b>{gn}</b>",
        f"🗓 {wd_label} · {full_date}",
        "",
        "· · ·",
        "",
    ]
    for i, slot in enumerate(snapshot.slots):
        time_part = _pair_time_display(i)
        pair_lbl = _pair_label(i)
        time_suffix = f" <i>({time_part})</i>" if time_part else ""
        lines.append(f"<b>{pair_lbl}</b>{time_suffix}")
        lines.append(_escape_slot_body(slot))
        lines.append("")
    return "\n".join(lines).rstrip()


def format_day_schedule_outcome_html(
    outcome: DayScheduleSnapshot | Literal["sunday"],
    *,
    group_name: str,
    target_date: date,
) -> str:
    """HTML для снимка дня или воскресенья."""
    if outcome == "sunday":
        return format_sunday_off_html(group_name, target_date)
    return format_day_schedule_html(outcome)
