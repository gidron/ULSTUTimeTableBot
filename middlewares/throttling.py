from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, throttle_time: int = 1):
        self.cache = TTLCache(maxsize=10_000, ttl=throttle_time)

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any],
    ) -> Any:

        if event.chat.id in self.cache:
            return
        else:
            self.cache[event.chat.id] = None

        return await handler(event, data)
