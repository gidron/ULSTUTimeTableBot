from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message
from database.models import User


class CheckUserIsActiveMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:

        tg_id = event.from_user.id
        user = await User.get_or_none(tg_id=tg_id)

        allowed_commands = ["/start", "/id"]

        if event.text in allowed_commands or (user and user.is_active):
            return await handler(event, data)

        return None
