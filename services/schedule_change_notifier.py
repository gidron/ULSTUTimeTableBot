from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from aiogram import Bot
from tortoise.expressions import Q

from database.models import (
    ScheduleChangeDigest,
    ScheduleSnapshot,
    User,
)
from services.image_renderer import PAIR_TIMES, WEEKDAY_NAMES
from services.network import UniversityClient

logger = logging.getLogger("default")


@dataclass(frozen=True)
class LessonEntry:
    name: str
    teacher: str
    room: str

    @property
    def stable_key(self) -> str:
        return f"{self.name}|{self.teacher}"


class ScheduleChangeNotifier:
    RUN_HOURS = (8, 13, 18, 21)

    async def run_forever(self, bot: Bot) -> None:
        while True:
            sleep_seconds = self._seconds_until_next_run()
            logger.info("Следующая проверка расписания через %s сек.", sleep_seconds)
            await asyncio.sleep(sleep_seconds)
            await self.check_and_notify(bot)

    async def check_and_notify(self, bot: Bot) -> None:
        groups = await self._get_target_groups()
        logger.info("Проверка изменений расписания запущена | groups_count=%s", len(groups))

        for group_name in groups:
            try:
                await self._process_group(bot, group_name)
            except Exception:
                logger.exception("Ошибка во время обработки группы | group=%s", group_name)

    async def _process_group(self, bot: Bot, group_name: str) -> None:
        now = datetime.now()
        async with UniversityClient(group_name=group_name) as client:
            current_week, payload = await client.get_current_week_and_timetable()

        week_key = str(current_week - 1)
        week_data = payload.get("response", {}).get("weeks", {}).get(week_key)
        if not isinstance(week_data, dict):
            logger.warning("Текущая неделя не найдена в payload | group=%s | week_key=%s", group_name, week_key)
            return

        week_slots = self._extract_week_slots(week_data=week_data, week_number=current_week)
        payload_hash = self._hash_payload(week_slots)

        snapshot = await ScheduleSnapshot.get_or_none(group_name=group_name)
        if snapshot is None:
            await ScheduleSnapshot.create(
                group_name=group_name,
                week_number=current_week,
                payload_hash=payload_hash,
                payload=week_slots,
            )
            logger.info("Создан baseline слепок без уведомления | group=%s", group_name)
            return

        old_slots = snapshot.payload if isinstance(snapshot.payload, list) else []
        changes = self._build_changes(old_slots=old_slots, new_slots=week_slots, now=now)

        snapshot.week_number = current_week
        snapshot.payload_hash = payload_hash
        snapshot.payload = week_slots
        await snapshot.save()

        if not changes:
            logger.info("Изменений нет | group=%s", group_name)
            return

        digest = self._hash_payload(changes)
        already_sent = await ScheduleChangeDigest.get_or_none(digest=digest)
        if already_sent is not None:
            logger.info("Повторный digest, уведомление не отправлено | group=%s", group_name)
            return

        await ScheduleChangeDigest.create(group_name=group_name, digest=digest)
        await self._notify_group_users(bot=bot, group_name=group_name, changes=changes)

    @staticmethod
    async def _get_target_groups() -> list[str]:
        rows = await User.filter(
            Q(is_active=True) & Q(group_name__not_isnull=True) & Q(notify_by_change=True)
        ).distinct().values_list("group_name", flat=True)
        return [group for group in rows if group]

    @staticmethod
    def _hash_payload(payload: object) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _pair_start_time(slot_index: int) -> tuple[int, int]:
        if slot_index >= len(PAIR_TIMES):
            return 0, 0
        time_text = PAIR_TIMES[slot_index].split("-", maxsplit=1)[0]
        hours, minutes = time_text.split(":")
        return int(hours), int(minutes)

    def _extract_week_slots(self, week_data: dict, week_number: int) -> list[dict]:
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
                lessons_normalized = self._normalize_lessons(slot_entries)
                slots.append(
                    {
                        "week_number": week_number,
                        "day_index": day_index,
                        "slot_index": slot_index,
                        "lessons": [lesson.__dict__ for lesson in lessons_normalized],
                    }
                )

        return slots

    @staticmethod
    def _normalize_lessons(slot_entries: object) -> list[LessonEntry]:
        if not isinstance(slot_entries, list):
            return []

        lessons: list[LessonEntry] = []
        for raw in slot_entries:
            if not isinstance(raw, dict):
                continue
            name = ScheduleChangeNotifier._normalize_text(raw.get("nameOfLesson", ""))
            teacher = ScheduleChangeNotifier._normalize_text(raw.get("teacher", ""))
            room = ScheduleChangeNotifier._normalize_text(raw.get("room", ""))
            if not name and not teacher and not room:
                continue
            lessons.append(LessonEntry(name=name, teacher=teacher, room=room))

        lessons.sort(key=lambda item: (item.name, item.teacher, item.room))
        return lessons

    def _build_changes(self, old_slots: list[dict], new_slots: list[dict], now: datetime) -> list[dict]:
        old_map = {(x["day_index"], x["slot_index"]): x for x in old_slots}
        new_map = {(x["day_index"], x["slot_index"]): x for x in new_slots}
        all_keys = sorted(set(old_map) | set(new_map))

        changes: list[dict] = []
        for day_index, slot_index in all_keys:
            if not self._is_future_slot(day_index=day_index, slot_index=slot_index, now=now):
                continue
            old_lessons = [
                LessonEntry(**lesson) for lesson in old_map.get((day_index, slot_index), {}).get("lessons", [])
            ]
            new_lessons = [
                LessonEntry(**lesson) for lesson in new_map.get((day_index, slot_index), {}).get("lessons", [])
            ]
            changes.extend(self._compare_slot(day_index, slot_index, old_lessons, new_lessons))

        return changes

    @staticmethod
    def _compare_slot(
        day_index: int,
        slot_index: int,
        old_lessons: list[LessonEntry],
        new_lessons: list[LessonEntry],
    ) -> list[dict]:
        changes: list[dict] = []
        old_full = Counter((lesson.name, lesson.teacher, lesson.room) for lesson in old_lessons)
        new_full = Counter((lesson.name, lesson.teacher, lesson.room) for lesson in new_lessons)

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
                            "day_index": day_index,
                            "slot_index": slot_index,
                            "lesson": {"name": name, "teacher": teacher, "room": room},
                        }
                    )
        return changes

    @staticmethod
    def _normalize_text(value: object) -> str:
        text = str(value or "").strip().lower()
        return re.sub(r"\s+", " ", text)

    def _is_future_slot(self, day_index: int, slot_index: int, now: datetime) -> bool:
        today = now.date()
        current_monday = today - timedelta(days=today.weekday())
        day_date = current_monday + timedelta(days=day_index)
        hour, minute = self._pair_start_time(slot_index)
        slot_start_dt = datetime(
            year=day_date.year,
            month=day_date.month,
            day=day_date.day,
            hour=hour,
            minute=minute,
        )
        return slot_start_dt >= now

    async def _notify_group_users(self, bot: Bot, group_name: str, changes: list[dict]) -> None:
        users = await User.filter(
            Q(is_active=True) & Q(group_name=group_name) & Q(notify_by_change=True)
        ).values_list("tg_id", flat=True)

        if not users:
            return

        text = self._render_message(group_name=group_name, changes=changes)
        for tg_id in users:
            try:
                await bot.send_message(chat_id=int(tg_id), text=text)
            except Exception:
                logger.exception("Не удалось отправить уведомление | tg_id=%s", tg_id)

    @staticmethod
    def _render_message(group_name: str, changes: list[dict]) -> str:
        lines = [f"Изменения в расписании ({group_name}):", ""]
        for change in changes:
            day_name = WEEKDAY_NAMES[change["day_index"]]
            pair_number = change["slot_index"] + 1
            pair_time = PAIR_TIMES[change["slot_index"]] if change["slot_index"] < len(PAIR_TIMES) else ""

            if change["type"] == "cancelled":
                lesson = change["lesson"]
                lines.append(
                    f"• {day_name}, {pair_number}-я пара ({pair_time}) — отмена: "
                    f"{lesson.get('name', 'Без названия')} | {lesson.get('teacher', 'Преподаватель не указан')}"
                )
                continue

            if change["type"] == "added":
                lesson = change["lesson"]
                lines.append(
                    f"• {day_name}, {pair_number}-я пара ({pair_time}) — добавлена пара: "
                    f"{lesson.get('name', 'Без названия')} | "
                    f"{lesson.get('teacher', 'Преподаватель не указан')} | "
                    f"ауд. {lesson.get('room', '—')}"
                )
                continue

            lines.append(
                f"• {day_name}, {pair_number}-я пара ({pair_time}) — аудитория изменена: "
                f"{change.get('lesson_name', 'Без названия')}, "
                f"{change.get('teacher', 'Преподаватель не указан')} "
                f"({change.get('old_room', '—')} -> {change.get('new_room', '—')})"
            )

        return "\n".join(lines)

    def _seconds_until_next_run(self) -> int:
        now = datetime.now()
        candidates = []
        for hour in self.RUN_HOURS:
            candidates.append(now.replace(hour=hour, minute=0, second=0, microsecond=0))

        future_candidates = [item for item in candidates if item > now]
        if future_candidates:
            target = min(future_candidates)
        else:
            target = candidates[0] + timedelta(days=1)

        return max(1, int((target - now).total_seconds()))
