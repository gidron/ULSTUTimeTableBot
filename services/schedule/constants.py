"""Общие константы расписания УлГТУ: дни недели, номера пар, интервалы времени.

Используются и при отрисовке изображения, и при уведомлениях об изменениях.
"""

from __future__ import annotations

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
PAIR_HEADERS = ["1-я", "2-я", "3-я", "4-я", "5-я", "6-я", "7-я", "8-я"]
PAIR_TIMES = [
    "08:30-09:50",
    "10:00-11:20",
    "11:30-12:50",
    "13:30-14:50",
    "15:00-16:20",
    "16:30-17:50",
    "18:00-19:20",
    "19:30-20:50",
]


def pair_slot_start_time(slot_index: int) -> tuple[int, int]:
    """Время начала пары по индексу слота: (час, минута); вне диапазона — (0, 0)."""
    if slot_index >= len(PAIR_TIMES):
        return 0, 0
    time_text = PAIR_TIMES[slot_index].split("-", maxsplit=1)[0]
    hours, minutes = time_text.split(":")
    return int(hours), int(minutes)
