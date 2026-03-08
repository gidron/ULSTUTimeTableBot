import logging
from typing import Iterable


logger = logging.getLogger("parser")


class TimetableParseError(Exception):
    pass


class TimetableParser:
    @staticmethod
    def get_weeks(payload: dict) -> list[tuple[str, dict]]:
        logger.debug("Извлечение недель из payload")
        weeks = payload.get("response", {}).get("weeks", {})
        if not isinstance(weeks, dict) or not weeks:
            logger.error("В ответе API нет блока response.weeks")
            raise TimetableParseError("В ответе API нет блока response.weeks")

        result = list(weeks.items())
        logger.debug("Недели извлечены | count=%s | keys=%s", len(result), [key for key, _ in result])
        return result

    @staticmethod
    def pick_week(payload: dict, week_kind: str, current_week_number: int | None = None) -> tuple[str, dict]:
        logger.debug(
            "Выбор недели | week_kind=%s | current_week_number=%s",
            week_kind,
            current_week_number,
        )
        weeks = TimetableParser.get_weeks(payload)

        if week_kind == "current":
            if current_week_number is not None:
                current_week_key = str(current_week_number)
                for week_key, week_data in weeks:
                    if week_key == current_week_key:
                        logger.debug("Выбрана текущая неделя | week_key=%s", week_key)
                        return week_key, week_data
            logger.debug("Текущая неделя не найдена, берём первую | week_key=%s", weeks[0][0])
            return weeks[0]

        if week_kind == "next":
            if current_week_number is not None:
                current_week_key = str(current_week_number)
                for idx, (week_key, _) in enumerate(weeks):
                    if week_key == current_week_key:
                        next_index = idx + 1
                        if next_index < len(weeks):
                            logger.debug("Выбрана следующая неделя | week_key=%s", weeks[next_index][0])
                            return weeks[next_index]
                        break
            if len(weeks) < 2:
                logger.error("Следующая неделя отсутствует в ответе API")
                raise TimetableParseError("Следующая неделя отсутствует в ответе API")
            logger.debug("Текущая неделя не найдена, берём вторую | week_key=%s", weeks[1][0])
            return weeks[1]

        logger.error("Неизвестный тип недели | week_kind=%s", week_kind)
        raise TimetableParseError(f"Неизвестный тип недели: {week_kind}")

    @staticmethod
    def normalize_week(week_number: str, week_data: dict, *, group_name: str, highlight_day_index: int | None = None) -> dict:
        logger.debug(
            "Нормализация недели | week_number=%s | group_name=%s | highlight_day_index=%s",
            week_number,
            group_name,
            highlight_day_index,
        )

        days = week_data.get("days", [])
        day_map = {day_item.get("day"): day_item for day_item in days if isinstance(day_item, dict)}
        logger.debug("Собрана карта дней | count=%s", len(day_map))

        normalized_days: list[dict] = []
        for day_idx in range(6):
            day_item = day_map.get(day_idx, {})
            lessons: list = day_item.get("lessons", []) if isinstance(day_item, dict) else []
            normalized_slots: list[str] = []

            logger.debug("Нормализация дня | day_idx=%s | lessons_count=%s", day_idx, len(lessons))

            for slot_index in range(8):
                lesson_entries = lessons[slot_index] if slot_index < len(lessons) else []
                slot_text = TimetableParser._format_slot(lesson_entries)
                normalized_slots.append(slot_text)

            normalized_days.append({
                "day_index": day_idx,
                "slots": normalized_slots,
                "is_current_day": highlight_day_index == day_idx,
            })

        result = {
            "group_name": group_name,
            "week_number": week_number,
            "days": normalized_days,
        }
        logger.debug("Нормализация завершена | days_count=%s", len(normalized_days))
        return result

    @staticmethod
    def _format_slot(lesson_entries: Iterable[dict]) -> str:
        entries = list(lesson_entries or [])
        logger.debug("Форматирование слота | entries_count=%s", len(entries))

        if not entries:
            return ""

        lines: list[str] = []
        for item in entries:
            lesson = item.get("nameOfLesson", "").strip()
            teacher = item.get("teacher", "").strip()
            room = item.get("room", "").strip()
            line = "\n".join(part for part in [lesson, teacher, room] if part)
            if line:
                lines.append(line)

        result = "\n\n".join(lines)
        logger.debug("Слот сформирован | text_length=%s", len(result))
        return result
