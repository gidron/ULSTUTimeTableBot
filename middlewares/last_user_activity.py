from datetime import date
from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message

from database.models import User


class LastUserActivityMiddleware(BaseMiddleware):
    """Обновляет last_day_online не чаще одного раза в календарный день."""

    def __init__(self) -> None:
        self.cache: dict[int, date] = {}

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
    ) -> Any:
        tg_id = event.from_user.id
        today = date.today()

        if not await User.get_or_none(tg_id=tg_id):
            return await handler(event, data)

        cached_day = self.cache.get(tg_id)
        if cached_day != today:
            username = event.from_user.username
            full_name = event.from_user.full_name

            user = await User.get(tg_id=tg_id)
            user.last_day_online = today
            user.username = username
            user.name = full_name
            await user.save()

            self.cache[tg_id] = today

        return await handler(event, data)
