"""Случайные пары слепков для превью текста уведомлений (без API и БД)."""

from __future__ import annotations

import random
from datetime import datetime

from . import change_detector
from .message_renderer import render_schedule_change_message

_LESSON_TITLES = (
    "математический анализ",
    "программирование",
    "базы данных",
    "операционные системы",
    "компьютерные сети",
    "технология программирования",
    "информатика",
    "физика",
)

_TEACHERS = (
    "иванов и.и.",
    "петрова а.с.",
    "сидоров п.п.",
    "козлова м.в.",
    "смирнов д.д.",
)

_ROOMS = ("301", "3-12", "2-08а", "4-15", "1-07", "5-22")


def _lesson() -> dict[str, str]:
    return {
        "name": random.choice(_LESSON_TITLES),
        "teacher": random.choice(_TEACHERS),
        "room": random.choice(_ROOMS),
    }


def _slot(
    week: int, day_index: int, slot_index: int, lessons: list[dict[str, str]]
) -> dict:
    return {
        "week_number": week,
        "day_index": day_index,
        "slot_index": slot_index,
        "lessons": [dict(x) for x in lessons],
    }


def _pick_distinct_pairs(n: int) -> list[tuple[int, int]]:
    pool = [(d, s) for d in range(6) for s in range(7)]
    return random.sample(pool, min(n, len(pool)))


def build_demo_notify_message(group_name: str) -> str:
    """Строит текст уведомления как в проде: случайные изменения на следующей учебной неделе."""
    api_current_week = random.randint(8, 40)
    # Только «следующая» неделя в слепке — should_notify_slot True для всех пар
    display_week = api_current_week + 1
    now = datetime.now()

    pairs = _pick_distinct_pairs(6)
    (d1, s1), (d2, s2), (d3, s3), (d4, s4), (d5, s5) = pairs[:5]

    old_slots: list[dict] = []
    new_slots: list[dict] = []

    # Смена аудитории (то же название и преподаватель)
    a = _lesson()
    r_old, r_new = random.sample(_ROOMS, 2)
    old_slots.append(_slot(display_week, d1, s1, [{**a, "room": r_old}]))
    new_slots.append(_slot(display_week, d1, s1, [{**a, "room": r_new}]))

    # Замена занятия (отмена + другое добавление в том же слоте)
    old_l, new_l = _lesson(), _lesson()
    while old_l["name"] == new_l["name"]:
        new_l = _lesson()
    old_slots.append(_slot(display_week, d2, s2, [old_l]))
    new_slots.append(_slot(display_week, d2, s2, [new_l]))

    # Только отмена
    old_slots.append(_slot(display_week, d3, s3, [_lesson()]))
    new_slots.append(_slot(display_week, d3, s3, []))

    # Только добавление (в old этого слота не было)
    new_slots.append(_slot(display_week, d4, s4, [_lesson()]))

    # Две пары в одном слоте: одна отменена, одна добавлена (остаток мультимножества)
    b1, b2 = _lesson(), _lesson()
    c1 = _lesson()
    old_slots.append(_slot(display_week, d5, s5, [b1, b2]))
    new_slots.append(_slot(display_week, d5, s5, [b2, c1]))

    changes = change_detector.build_changes(
        old_slots=old_slots,
        new_slots=new_slots,
        now=now,
        api_current_week=api_current_week,
    )

    text = render_schedule_change_message(
        group_name=group_name,
        changes=changes,
        api_current_week=api_current_week,
    )
    return text or "Не удалось сформировать превью (пустой список изменений)."
