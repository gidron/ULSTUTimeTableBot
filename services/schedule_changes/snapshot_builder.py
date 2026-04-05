"""Построение нормализованного слепка расписания (текущая + следующая неделя) для хеширования."""

from __future__ import annotations

import logging
import re

from services.data_parser import TimetableParseError, TimetableParser
from services.schedule_changes.models import LessonEntry

logger = logging.getLogger("default")


def sort_slots_for_hash(slots: list[dict]) -> list[dict]:
    """Сортирует слоты для детерминированного JSON и хеша."""
    return sorted(
        slots, key=lambda s: (s["week_number"], s["day_index"], s["slot_index"])
    )


def normalize_lesson_text(value: object) -> str:
    """Нижний регистр, схлопывание пробелов — для сравнения строк из API."""
    text = str(value or "").strip().lower()
    return re.sub(r"\s+", " ", text)


def normalize_lessons(slot_entries: object) -> list[LessonEntry]:
    """Превращает сырой список занятий слота в отсортированный список LessonEntry."""
    if not isinstance(slot_entries, list):
        return []

    lessons: list[LessonEntry] = []
    for raw in slot_entries:
        if not isinstance(raw, dict):
            continue
        name = normalize_lesson_text(raw.get("nameOfLesson", ""))
        teacher = normalize_lesson_text(raw.get("teacher", ""))
        room = normalize_lesson_text(raw.get("room", ""))
        if not name and not teacher and not room:
            continue
        lessons.append(LessonEntry(name=name, teacher=teacher, room=room))

    lessons.sort(key=lambda item: (item.name, item.teacher, item.room))
    return lessons


def extract_week_slots(week_data: dict, week_number: int) -> list[dict]:
    """Вытаскивает все слоты одной недели из ответа API в плоский список словарей."""
    slots: list[dict] = []

    for day_payload in week_data.get("days", []):
        if not isinstance(day_payload, dict):
            continue
        day_index = day_payload.get("day")
        if not isinstance(day_index, int) or day_index < 0 or day_index > 5:
            continue

        lessons = day_payload.get("lessons", [])
        if not isinstance(lessons, list):
            continue

        for slot_index, slot_entries in enumerate(lessons):
            lessons_normalized = normalize_lessons(slot_entries)
            slots.append(
                {
                    "week_number": week_number,
                    "day_index": day_index,
                    "slot_index": slot_index,
                    "lessons": [lesson.__dict__ for lesson in lessons_normalized],
                }
            )

    return slots


def build_two_week_slots(payload: dict, api_current_week: int) -> list[dict]:
    """Текущая и следующая неделя в одном слепке (стабильный хеш при смене окна API)."""
    try:
        cur_key, cur_data = TimetableParser.pick_week(
            payload, "current", api_current_week
        )
    except TimetableParseError:
        logger.warning(
            "pick_week(current) failed | api_current_week=%s", api_current_week
        )
        return []

    display_current = int(cur_key) + 1
    slots = extract_week_slots(week_data=cur_data, week_number=display_current)

    try:
        nxt_key, nxt_data = TimetableParser.pick_week(payload, "next", api_current_week)
    except TimetableParseError:
        logger.info(
            "Next week unavailable, snapshot limited to current week | display_week=%s",
            display_current,
        )
        return sort_slots_for_hash(slots)

    display_next = int(nxt_key) + 1
    slots.extend(extract_week_slots(week_data=nxt_data, week_number=display_next))

    return sort_slots_for_hash(slots)
