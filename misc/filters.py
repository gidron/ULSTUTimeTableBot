from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from database.models import User


class IsNotActiveUser(Filter):
    async def __call__(self, message: Message):
        if await User.filter(tg_id=str(message.from_user.id)).exists():
            user = await User.get(tg_id=str(message.from_user.id))
            return not user.is_active
        return False


class IsAdminUser(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user is None:
            return False
        user = await User.get_or_none(tg_id=str(event.from_user.id))
        return bool(user and user.is_admin)
