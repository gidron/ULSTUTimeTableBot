"""Разбор ответа API time.ulstu.ru: недели, нормализация под рендер и слепки."""

from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger("parser")


class TimetableParseError(Exception):
    """Некорректная или неполная структура расписания в ответе API."""


class TimetableParser:
    """Статические методы выбора недели и приведения данных к виду для картинки."""

    @staticmethod
    def get_weeks(payload: dict) -> list[tuple[str, dict]]:
        logger.debug("Extracting weeks from API payload")
        weeks = payload.get("response", {}).get("weeks", {})
        if not isinstance(weeks, dict) or not weeks:
            logger.error("API response missing response.weeks")
            raise TimetableParseError("API response has no response.weeks block")

        result = list(weeks.items())
        logger.debug(
            "Weeks extracted | count=%s | keys=%s",
            len(result),
            [key for key, _ in result],
        )
        return result

    @staticmethod
    def pick_week(
        payload: dict, week_kind: str, current_week_number: int | None = None
    ) -> tuple[str, dict]:
        logger.debug(
            "Picking week | week_kind=%s | current_week_number=%s",
            week_kind,
            current_week_number,
        )

        weeks = payload.get("response", {}).get("weeks", {})
        if not isinstance(weeks, dict) or not weeks:
            logger.error("API response missing response.weeks")
            raise TimetableParseError("API response has no response.weeks block")

        sorted_keys = sorted(weeks.keys(), key=int)
        logger.debug("Available week keys | keys=%s", sorted_keys)

        if week_kind == "current":
            if current_week_number is not None:
                current_key = str(max(0, current_week_number - 1))
                if current_key in weeks:
                    logger.debug("Selected current week | key=%s", current_key)
                    return current_key, weeks[current_key]

            first_key = sorted_keys[0]
            logger.debug(
                "Current week not matched by current_week_number, using first available | key=%s",
                first_key,
            )
            return first_key, weeks[first_key]

        if week_kind == "next":
            if current_week_number is None:
                logger.error("Cannot resolve next week without current_week_number")
                raise TimetableParseError(
                    "Cannot determine next week without current_week_number"
                )

            next_key = "1" if current_week_number == 0 else str(current_week_number)
            if next_key in weeks:
                logger.debug("Selected next week | key=%s", next_key)
                return next_key, weeks[next_key]

            logger.warning(
                "Next week not in API response | current_week_number=%s | expected_key=%s | available_keys=%s",
                current_week_number,
                next_key,
                sorted_keys,
            )
            raise TimetableParseError(
                "Next week is not available in the API response yet"
            )

        logger.error("Unknown week_kind | week_kind=%s", week_kind)
        raise TimetableParseError(f"Unknown week_kind: {week_kind}")

    @staticmethod
    def normalize_week(
        week_number: str,
        week_data: dict,
        *,
        group_name: str,
        highlight_day_index: int | None = None,
        schedule_title_prefix: str = "Расписание группы:",
        include_study_group_in_slots: bool = False,
    ) -> dict:
        logger.debug(
            "Normalizing week | week_number=%s | group_name=%s | highlight_day_index=%s",
            week_number,
            group_name,
            highlight_day_index,
        )

        days = week_data.get("days", [])
        day_map = {
            day_item.get("day"): day_item
            for day_item in days
            if isinstance(day_item, dict)
        }
        logger.debug("Built day map | count=%s", len(day_map))

        normalized_days: list[dict] = []
        for day_idx in range(6):
            day_item = day_map.get(day_idx, {})
            lessons: list = (
                day_item.get("lessons", []) if isinstance(day_item, dict) else []
            )
            normalized_slots: list[str] = []

            logger.debug(
                "Normalizing day | day_idx=%s | lessons_count=%s", day_idx, len(lessons)
            )

            for slot_index in range(8):
                lesson_entries = (
                    lessons[slot_index] if slot_index < len(lessons) else []
                )
                slot_text = TimetableParser._format_slot(
                    lesson_entries,
                    include_study_group_in_slots=include_study_group_in_slots,
                )
                normalized_slots.append(slot_text)

            normalized_days.append(
                {
                    "day_index": day_idx,
                    "slots": normalized_slots,
                    "is_current_day": highlight_day_index == day_idx,
                }
            )

        result = {
            "group_name": group_name,
            "schedule_title_prefix": schedule_title_prefix,
            "week_number": week_number,
            "days": normalized_days,
        }
        logger.debug("Normalization complete | days_count=%s", len(normalized_days))
        return result

    @staticmethod
    def _format_slot(
        lesson_entries: Iterable[dict],
        *,
        include_study_group_in_slots: bool = False,
    ) -> str:
        entries = list(lesson_entries or [])
        logger.debug("Formatting slot | entries_count=%s", len(entries))

        if not entries:
            return ""

        groups: list[str] = []
        for item in entries:
            g = (item.get("group") or "").strip()
            if g and g not in groups:
                groups.append(g)

        def _student_block(item: dict) -> str:
            lesson = (item.get("nameOfLesson") or "").strip()
            teacher = (item.get("teacher") or "").strip()
            room = (item.get("room") or "").strip()
            parts = [lesson, teacher, room]
            return "\n".join(p for p in parts if p)

        def _teacher_block(item: dict) -> str:
            """Расписание преподавателя: в ячейке не дублируем ФИО преподавателя."""
            lesson = (item.get("nameOfLesson") or "").strip()
            room = (item.get("room") or "").strip()
            parts = [lesson, room]
            return "\n".join(p for p in parts if p)

        def _dedupe_blocks(blocks: list[str]) -> list[str]:
            """Одинаковые блоки (общая пара для нескольких групп в API) — один раз."""
            seen: set[str] = set()
            out: list[str] = []
            for b in blocks:
                if not b or b in seen:
                    continue
                seen.add(b)
                out.append(b)
            return out

        if include_study_group_in_slots:
            blocks = _dedupe_blocks([_teacher_block(e) for e in entries])

            if len(groups) >= 2:
                head = " ".join(groups)
                body = "\n\n".join(blocks)
                result = f"{head}\n\n{body}" if body else head
                logger.debug(
                    "Slot text built (teacher, multi-group) | text_length=%s",
                    len(result),
                )
                return result

            if len(entries) == 1:
                item = entries[0]
                sg = (item.get("group") or "").strip()
                lesson = (item.get("nameOfLesson") or "").strip()
                room = (item.get("room") or "").strip()
                parts = [sg, lesson, room]
                result = "\n".join(p for p in parts if p)
                logger.debug(
                    "Slot text built (teacher, single) | text_length=%s", len(result)
                )
                return result

            if len(groups) == 1:
                head = groups[0]
                body = "\n\n".join(blocks)
                result = f"{head}\n\n{body}" if body else head
                logger.debug(
                    "Slot text built (teacher, one group) | text_length=%s", len(result)
                )
                return result

            result = "\n\n".join(blocks)
            logger.debug(
                "Slot text built (teacher, no groups) | text_length=%s", len(result)
            )
            return result

        if len(groups) >= 2:
            blocks = _dedupe_blocks([_student_block(e) for e in entries])
            head = " ".join(groups)
            body = "\n\n".join(blocks)
            result = f"{head}\n\n{body}" if body else head
            logger.debug(
                "Slot text built (student, multi-group header) | text_length=%s",
                len(result),
            )
            return result

        lines: list[str] = []
        for item in entries:
            line = _student_block(item)
            if line:
                lines.append(line)

        result = "\n\n".join(_dedupe_blocks(lines))
        logger.debug("Slot text built | text_length=%s", len(result))
        return result
