"""Текст уведомления пользователю Telegram об изменениях расписания."""

from __future__ import annotations

from services.schedule_constants import PAIR_TIMES, WEEKDAY_NAMES


def render_schedule_change_message(group_name: str, changes: list[dict]) -> str:
    """Формирует многострочное сообщение по списку изменений (cancelled / added / room_changed)."""
    lines = [f"Изменения в расписании ({group_name}):", ""]
    for change in changes:
        week_label = ""
        wn = change.get("week_number")
        if isinstance(wn, int):
            week_label = f"нед. {wn}, "
        day_name = WEEKDAY_NAMES[change["day_index"]]
        pair_number = change["slot_index"] + 1
        pair_time = (
            PAIR_TIMES[change["slot_index"]]
            if change["slot_index"] < len(PAIR_TIMES)
            else ""
        )

        if change["type"] == "cancelled":
            lesson = change["lesson"]
            lines.append(
                f"• {week_label}{day_name}, {pair_number}-я пара ({pair_time}) — отмена: "
                f"{lesson.get('name', 'Без названия')} | {lesson.get('teacher', 'Преподаватель не указан')}"
            )
            continue

        if change["type"] == "added":
            lesson = change["lesson"]
            lines.append(
                f"• {week_label}{day_name}, {pair_number}-я пара ({pair_time}) — добавлена пара: "
                f"{lesson.get('name', 'Без названия')} | "
                f"{lesson.get('teacher', 'Преподаватель не указан')} | "
                f"ауд. {lesson.get('room', '—')}"
            )
            continue

        lines.append(
            f"• {week_label}{day_name}, {pair_number}-я пара ({pair_time}) — аудитория изменена: "
            f"{change.get('lesson_name', 'Без названия')}, "
            f"{change.get('teacher', 'Преподаватель не указан')} "
            f"({change.get('old_room', '—')} -> {change.get('new_room', '—')})"
        )

    return "\n".join(lines)
