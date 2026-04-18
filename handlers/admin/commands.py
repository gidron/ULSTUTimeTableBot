from __future__ import annotations

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.models import User
from handlers.admin.tools.texts import build_menu_text
from keyboards.admin import admin_menu_kb
from misc.admin_audit import log_admin_action
from misc.filters import IsAdminUser

router = Router(name="admin_commands")


@router.message(IsAdminUser(), Command("admin"))
async def admin_command(message: Message, state: FSMContext) -> None:
    """Открыть инлайн-админку."""
    await state.set_state()
    await message.answer(build_menu_text(), reply_markup=admin_menu_kb())


@router.message(IsAdminUser(), Command("broadcast"))
async def broadcast(message: Message) -> None:
    """Рассылка копии reply-сообщения всем активным пользователям."""
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
        if user.tg_id == str(message.from_user.id):
            continue
        try:
            await message.bot.copy_message(
                chat_id=int(user.tg_id),
                from_chat_id=message.chat.id,
                message_id=reply.message_id,
            )
            ok += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    log_admin_action(
        actor_tg_id=message.from_user.id,
        action="broadcast",
        ok=ok,
        failed=failed,
    )
    await message.answer(
        f"Готово. Доставлено: <b>{ok}</b>, не удалось отправить: <b>{failed}</b>."
    )


# --- Legacy-команды (оставлены для совместимости; основной UI — /admin) ---


async def _toggle_active(message: Message, command: CommandObject, target: bool) -> None:
    tg_id = (command.args or "").strip()
    user = await User.get_or_none(tg_id=tg_id)
    if user is None:
        await message.answer("Такой tg_id не найден!")
        return
    user.is_active = target
    await user.save()
    log_admin_action(
        actor_tg_id=message.from_user.id,
        action="unban" if target else "ban",
        target_tg_id=int(user.tg_id),
        via="legacy_command",
    )
    await message.answer("Пользователь добавлен!" if target else "Пользователь забанен!")


@router.message(IsAdminUser(), Command("add"))
async def add_user(message: Message, command: CommandObject) -> None:
    await _toggle_active(message, command, target=True)


@router.message(IsAdminUser(), Command("ban"))
async def ban_user(message: Message, command: CommandObject) -> None:
    await _toggle_active(message, command, target=False)


@router.message(IsAdminUser(), Command("remove"))
async def remove_user(message: Message, command: CommandObject) -> None:
    tg_id = (command.args or "").strip()
    user = await User.get_or_none(tg_id=tg_id)
    if user is None:
        await message.answer("Такой tg_id не найден!")
        return
    target_id = int(user.tg_id)
    await user.delete()
    log_admin_action(
        actor_tg_id=message.from_user.id,
        action="delete_user",
        target_tg_id=target_id,
        via="legacy_command",
    )
    await message.answer("Пользователь удален!")


@router.message(IsAdminUser(), Command("list"))
async def list_users(message: Message) -> None:
    """Старый текстовый список — оставлен как быстрый дамп."""
    users = await User.all().order_by("group_name")
    text = ""
    for user in users:
        row = (
            f"{user.group_name} - {user.name} - "
            f"@{user.username} - <code>{user.tg_id}</code>\n"
        )
        if user.is_active:
            row = "✔" + row
        else:
            row = "❌" + row
        if user.is_admin:
            row = "💀" + row
        text += row
    await message.answer(text or "Пусто.")
