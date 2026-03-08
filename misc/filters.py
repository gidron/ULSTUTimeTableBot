from aiogram.filters import Filter
from aiogram.types import Message

from database.models import User


class IsNotActiveUser(Filter):
    async def __call__(self, message: Message):
        if await User.filter(tg_id=message.from_user.id).exists():
            user = await User.get(tg_id=message.from_user.id)
            return not user.is_active
        return False


class IsAdminUser(Filter):
    async def __call__(self, message: Message):
        if await User.filter(tg_id=message.from_user.id).exists():
            user = await User.get(tg_id=message.from_user.id)
            return user.is_admin
        return False
