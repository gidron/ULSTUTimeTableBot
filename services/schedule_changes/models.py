"""Модели данных для сравнения слотов расписания."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LessonEntry:
    """Одна запись занятия в слоте (имя, преподаватель, аудитория), нормализованный текст."""

    name: str
    teacher: str
    room: str

    @property
    def stable_key(self) -> str:
        """Ключ для группировки без учёта аудитории (смена аудитории отдельно)."""
        return f"{self.name}|{self.teacher}"
