"""Подсистема уведомлений об изменениях расписания (слепки, diff, рассылка)."""

from services.schedule_changes.notifier import ScheduleChangeNotifier

__all__ = ["ScheduleChangeNotifier"]
