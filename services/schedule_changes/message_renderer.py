"""Текст уведомления пользователю Telegram об изменениях расписания."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from services.schedule.constants import PAIR_HEADERS, PAIR_TIMES, WEEKDAY_NAMES
from services.schedule.week_dates import day_calendar_date

SCHEDULE_CHANGE_NOTIFY_FOOTER = (
    "\n\n🔕 <i>Если не хочешь получать сообщения об изменениях в расписании, "
    "то можешь их выключить в профиле — /profile</i>"
)


def _pair_time_display(slot_index: int) -> str:
    """Интервал пары с типографским тире, как в примере: 10:00–11:20."""
    if slot_index < 0 or slot_index >= len(PAIR_TIMES):
        return ""
    return PAIR_TIMES[slot_index].replace("-", "–", 1)


def _pair_label(slot_index: int) -> str:
    if 0 <= slot_index < len(PAIR_HEADERS):
        return f"{PAIR_HEADERS[slot_index]} пара"
    return f"{slot_index + 1}-я пара"


def _lesson_line(lesson: dict, *, include_room: bool) -> str:
    name = lesson.get("name") or "Без названия"
    teacher = lesson.get("teacher") or "Преподаватель не указан"
    base = f"{name} — {teacher}"
    if not include_room:
        return base
    room = lesson.get("room")
    room_text = room if room not in (None, "", "—") else "—"
    return f"{base} (ауд. {room_text})"


def _day_header_line(
    day_index: int,
    week_number: int,
    api_current_week: int,
    ref_today: date,
) -> str:
    """Одна строка: день недели и дата в скобках, как «Сб (14.04)»."""
    when = day_calendar_date(
        day_index,
        week_number,
        api_current_week,
        today=ref_today,
    )
    label = (
        WEEKDAY_NAMES[day_index] if day_index < len(WEEKDAY_NAMES) else str(day_index)
    )
    return f"{label} ({when.strftime('%d.%m')})"


def _slot_display_units(events: list[dict]) -> list[dict]:
    """Превращает сырые события слота в упорядоченные блоки для вывода."""
    room_changed = [e for e in events if e.get("type") == "room_changed"]
    cancelled = [e for e in events if e.get("type") == "cancelled"]
    added = [e for e in events if e.get("type") == "added"]

    units: list[dict] = []
    for rc in room_changed:
        units.append({"kind": "room_swap", "data": rc})

    pair_n = min(len(cancelled), len(added))
    for i in range(pair_n):
        units.append(
            {
                "kind": "lesson_swap",
                "cancelled": cancelled[i]["lesson"],
                "added": added[i]["lesson"],
            }
        )
    for j in range(pair_n, len(cancelled)):
        units.append({"kind": "cancelled", "lesson": cancelled[j]["lesson"]})
    for j in range(pair_n, len(added)):
        units.append({"kind": "added", "lesson": added[j]["lesson"]})

    return units


def _append_cancelled_block(lines: list[str], slot_index: int, lesson: dict) -> None:
    pair_time = _pair_time_display(slot_index)
    pair_lbl = _pair_label(slot_index)
    time_part = f" ({pair_time})" if pair_time else ""
    lines.append(f"— ❌ {pair_lbl}{time_part}")
    lines.append(_lesson_line(lesson, include_room=False))


def _append_added_block(lines: list[str], slot_index: int, lesson: dict) -> None:
    pair_time = _pair_time_display(slot_index)
    pair_lbl = _pair_label(slot_index)
    time_part = f" ({pair_time})" if pair_time else ""
    lines.append(f"— ➕ {pair_lbl}{time_part}")
    lines.append(_lesson_line(lesson, include_room=True))


def _append_room_changed_block(lines: list[str], slot_index: int, ch: dict) -> None:
    pair_time = _pair_time_display(slot_index)
    pair_lbl = _pair_label(slot_index)
    time_part = f" ({pair_time})" if pair_time else ""
    name = ch.get("lesson_name") or "Без названия"
    teacher = ch.get("teacher") or "Преподаватель не указан"
    old_r = ch.get("old_room")
    new_r = ch.get("new_room")
    old_room = old_r if old_r not in (None, "", "—") else "—"
    new_room = new_r if new_r not in (None, "", "—") else "—"
    lines.append(f"— 🔁 {pair_lbl}{time_part} — замена")
    lines.append(f"было: {name} — {teacher} (ауд. {old_room})")
    lines.append(f"стало: {name} — {teacher} (ауд. {new_room})")


def _append_lesson_swap_block(
    lines: list[str], slot_index: int, old_lesson: dict, new_lesson: dict
) -> None:
    pair_time = _pair_time_display(slot_index)
    pair_lbl = _pair_label(slot_index)
    time_part = f" ({pair_time})" if pair_time else ""
    lines.append(f"— 🔁 {pair_lbl}{time_part} — замена")
    old_line = _lesson_line(old_lesson, include_room=False)
    old_room = old_lesson.get("room")
    if old_room not in (None, "", "—"):
        old_line = f"{old_line} (ауд. {old_room})"
    lines.append(f"было: {old_line}")
    lines.append(f"стало: {_lesson_line(new_lesson, include_room=True)}")


def _render_one_day(
    lines: list[str],
    day_index: int,
    week_number: int,
    api_current_week: int,
    ref_today: date,
    day_events: list[dict],
) -> None:
    lines.append(_day_header_line(day_index, week_number, api_current_week, ref_today))

    by_slot: dict[int, list[dict]] = defaultdict(list)
    for ch in day_events:
        by_slot[ch["slot_index"]].append(ch)

    for slot_index in sorted(by_slot.keys()):
        units = _slot_display_units(by_slot[slot_index])
        for u in units:
            if u["kind"] == "room_swap":
                _append_room_changed_block(lines, slot_index, u["data"])
            elif u["kind"] == "lesson_swap":
                _append_lesson_swap_block(
                    lines,
                    slot_index,
                    u["cancelled"],
                    u["added"],
                )
            elif u["kind"] == "cancelled":
                _append_cancelled_block(lines, slot_index, u["lesson"])
            elif u["kind"] == "added":
                _append_added_block(lines, slot_index, u["lesson"])
            lines.append("")

    if lines and lines[-1] == "":
        lines.pop()


def render_schedule_change_message(
    group_name: str,
    changes: list[dict],
    *,
    api_current_week: int,
    today: date | None = None,
) -> str:
    """Формирует сообщение: отдельный блок на каждую учебную неделю; день — «Вт (07.04)»."""
    if not changes:
        return ""

    ref_today = today or date.today()

    by_week: dict[int, list[dict]] = defaultdict(list)
    for ch in changes:
        wn = ch.get("week_number")
        if not isinstance(wn, int):
            continue
        by_week[wn].append(ch)

    week_blocks: list[str] = []
    for week_number in sorted(by_week.keys()):
        lines: list[str] = [
            f"Изменения в расписании ({group_name}, нед. {week_number})",
            "",
        ]
        wk = by_week[week_number]
        by_day: dict[int, list[dict]] = defaultdict(list)
        for ch in wk:
            by_day[ch["day_index"]].append(ch)

        day_indices = sorted(by_day.keys())
        for di, day_index in enumerate(day_indices):
            _render_one_day(
                lines,
                day_index,
                week_number,
                api_current_week,
                ref_today,
                by_day[day_index],
            )
            if di < len(day_indices) - 1:
                lines.append("")

        week_blocks.append("\n".join(lines))

    return "\n\n".join(week_blocks) + SCHEDULE_CHANGE_NOTIFY_FOOTER
