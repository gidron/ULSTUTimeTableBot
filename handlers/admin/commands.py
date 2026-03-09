from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from database.models import User
from misc.filters import IsAdminUser

router = Router(name="admin_commands")


@router.message(IsAdminUser(), Command("add"))
async def add_user(message: Message, command: CommandObject):
    tg_id = command.args

    if await User.filter(tg_id=tg_id).exists():
        user = await User.get(tg_id=tg_id)
        user.is_active = True
        await user.save()
        await message.answer("Пользователь добавлен!")
    else:
        await message.answer("Такой tg_id не найден!")


@router.message(IsAdminUser(), Command("remove"))
async def remove_user(message: Message, command: CommandObject):
    tg_id = command.args

    if await User.filter(tg_id=tg_id).exists():
        user = await User.get(tg_id=tg_id)
        user.is_active = False
        await user.save()
        await message.answer("Пользователь удален!")
    else:
        await message.answer("Такой tg_id не найден!")


@router.message(IsAdminUser(), Command("list"))
async def list_users(message: Message):
    users = await User.all().order_by("group_name")
    text = ""

    for user in users:
        row = f"{user.group_name} - {user.name} - @{user.username} - `{user.tg_id}`\n"

        if user.is_active:
            row = "✔" + row
        else:
            row = "❌" + row

        if user.is_admin:
           row = "💀" + row

        text += row

    await message.answer(text)
