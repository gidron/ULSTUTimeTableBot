"""Сравнение старого и нового слепка: какие пары изменились и что отправлять в уведомлении."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

from services.schedule_changes.models import LessonEntry
from services.schedule_constants import pair_slot_start_time


def normalize_slot_list(slots: list[dict], api_current_week: int) -> list[dict]:
    """Дополняет week_number у старых записей без поля — считаем неделей api_current_week."""
    out: list[dict] = []
    for s in slots:
        if not isinstance(s, dict):
            continue
        wn = s.get("week_number", api_current_week)
        if not isinstance(wn, int):
            try:
                wn = int(wn)
            except (TypeError, ValueError):
                wn = api_current_week
        row = dict(s)
        row["week_number"] = wn
        out.append(row)
    return out


def compare_slot(
    week_number: int,
    day_index: int,
    slot_index: int,
    old_lessons: list[LessonEntry],
    new_lessons: list[LessonEntry],
) -> list[dict]:
    """События по одному слоту: отмены, добавления, смена аудитории (мультимножества)."""
    changes: list[dict] = []
    old_full = Counter(
        (lesson.name, lesson.teacher, lesson.room) for lesson in old_lessons
    )
    new_full = Counter(
        (lesson.name, lesson.teacher, lesson.room) for lesson in new_lessons
    )

    removed = old_full - new_full
    added = new_full - old_full

    removed_by_base: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    added_by_base: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for (name, teacher, room), count in removed.items():
        removed_by_base[(name, teacher)][room] += count
    for (name, teacher, room), count in added.items():
        added_by_base[(name, teacher)][room] += count

    for base_key in set(removed_by_base) & set(added_by_base):
        name, teacher = base_key
        removed_rooms = removed_by_base[base_key]
        added_rooms = added_by_base[base_key]
        for old_room, old_count in list(removed_rooms.items()):
            if old_count <= 0:
                continue
            for new_room, new_count in list(added_rooms.items()):
                if new_count <= 0 or old_room == new_room:
                    continue
                match_count = min(old_count, new_count)
                for _ in range(match_count):
                    changes.append(
                        {
                            "type": "room_changed",
                            "week_number": week_number,
                            "day_index": day_index,
                            "slot_index": slot_index,
                            "lesson_name": name,
                            "teacher": teacher,
                            "old_room": old_room,
                            "new_room": new_room,
                        }
                    )
                removed_rooms[old_room] -= match_count
                added_rooms[new_room] -= match_count
                old_count -= match_count
                if old_count <= 0:
                    break

    for (name, teacher), rooms_counter in removed_by_base.items():
        for room, count in rooms_counter.items():
            for _ in range(max(0, count)):
                changes.append(
                    {
                        "type": "cancelled",
                        "week_number": week_number,
                        "day_index": day_index,
                        "slot_index": slot_index,
                        "lesson": {"name": name, "teacher": teacher, "room": room},
                    }
                )

    for (name, teacher), rooms_counter in added_by_base.items():
        for room, count in rooms_counter.items():
            for _ in range(max(0, count)):
                changes.append(
                    {
                        "type": "added",
                        "week_number": week_number,
                        "day_index": day_index,
                        "slot_index": slot_index,
                        "lesson": {"name": name, "teacher": teacher, "room": room},
                    }
                )
    return changes


def should_notify_slot(
    week_number: int,
    day_index: int,
    slot_index: int,
    now: datetime,
    api_current_week: int,
) -> bool:
    """Текущая неделя API: только пары, которые ещё не начались; следующая — все."""
    if week_number == api_current_week + 1:
        return True
    if week_number != api_current_week:
        return False
    today = now.date()
    current_monday = today - timedelta(days=today.weekday())
    day_date = current_monday + timedelta(days=day_index)
    hour, minute = pair_slot_start_time(slot_index)
    slot_start_dt = datetime(
        year=day_date.year,
        month=day_date.month,
        day=day_date.day,
        hour=hour,
        minute=minute,
    )
    return slot_start_dt >= now


def build_changes(
    old_slots: list[dict],
    new_slots: list[dict],
    now: datetime,
    api_current_week: int,
) -> list[dict]:
    """Полный список изменений по пересечению недель с учётом фильтра should_notify_slot."""
    old_norm = normalize_slot_list(old_slots, api_current_week)
    new_norm = normalize_slot_list(new_slots, api_current_week)

    old_weeks = {s["week_number"] for s in old_norm}
    new_weeks = {s["week_number"] for s in new_norm}
    common_weeks = old_weeks & new_weeks

    old_map = {(s["week_number"], s["day_index"], s["slot_index"]): s for s in old_norm}
    new_map = {(s["week_number"], s["day_index"], s["slot_index"]): s for s in new_norm}

    all_keys = sorted(set(old_map) | set(new_map))
    changes: list[dict] = []
    for week_number, day_index, slot_index in all_keys:
        if week_number not in common_weeks:
            continue
        if not should_notify_slot(
            week_number=week_number,
            day_index=day_index,
            slot_index=slot_index,
            now=now,
            api_current_week=api_current_week,
        ):
            continue
        old_lessons = [
            LessonEntry(**lesson)
            for lesson in old_map.get((week_number, day_index, slot_index), {}).get(
                "lessons", []
            )
        ]
        new_lessons = [
            LessonEntry(**lesson)
            for lesson in new_map.get((week_number, day_index, slot_index), {}).get(
                "lessons", []
            )
        ]
        changes.extend(
            compare_slot(week_number, day_index, slot_index, old_lessons, new_lessons)
        )

    return changes
