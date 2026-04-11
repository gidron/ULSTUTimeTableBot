"""Подсистема уведомлений об изменениях расписания (слепки, diff, рассылка)."""

from __future__ import annotations

__all__ = ["ScheduleChangeNotifier"]


def __getattr__(name: str):
    if name == "ScheduleChangeNotifier":
        from services.schedule_changes.notifier import ScheduleChangeNotifier

        return ScheduleChangeNotifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
