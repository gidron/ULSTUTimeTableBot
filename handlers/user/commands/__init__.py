"""Текстовые команды и ответы пользователя (/start, недели, профиль, /day, …)."""

from .common import router as user_commands_router
from .day import router as day_schedule_router

__all__ = ("day_schedule_router", "user_commands_router")
