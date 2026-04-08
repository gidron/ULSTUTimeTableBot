from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
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


@router.message(IsAdminUser(), Command("ban"))
async def ban_user(message: Message, command: CommandObject):
    tg_id = command.args

    if await User.filter(tg_id=tg_id).exists():
        user = await User.get(tg_id=tg_id)
        user.is_active = False
        await user.save()
        await message.answer("Пользователь забанен!")
    else:
        await message.answer("Такой tg_id не найден!")


@router.message(IsAdminUser(), Command("remove"))
async def remove_user(message: Message, command: CommandObject):
    tg_id = command.args

    if await User.filter(tg_id=tg_id).exists():
        user = await User.get(tg_id=tg_id)
        await user.delete()
        await message.answer("Пользователь удален!")
    else:
        await message.answer("Такой tg_id не найден!")


@router.message(IsAdminUser(), Command("broadcast"))
async def broadcast(message: Message):
    reply = message.reply_to_message
    if reply is None:
        await message.answer(
            "Ответь этой командой на сообщение, которое нужно разослать "
            "всем активным пользователям — бот отправит им его копию."
        )
        return

    users = await User.filter(is_active=True)
    ok = 0
    failed = 0
    for user in users:
        try:
            await message.bot.copy_message(
                chat_id=int(user.tg_id),
                from_chat_id=message.chat.id,
                message_id=reply.message_id,
            )
            ok += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    await message.answer(
        f"Готово. Доставлено: <b>{ok}</b>, не удалось отправить: <b>{failed}</b>."
    )


@router.message(IsAdminUser(), Command("list"))
async def list_users(message: Message):
    users = await User.all().order_by("group_name")
    text = ""

    for user in users:
        row = f"{user.group_name} - {user.name} - @{user.username} - <code>{user.tg_id}</code>\n"

        if user.is_active:
            row = "✔" + row
        else:
            row = "❌" + row

        if user.is_admin:
            row = "💀" + row

        text += row

    await message.answer(text)
