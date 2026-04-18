"""Команда /day и сообщение «ДД.ММ» в default_state."""

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import default_state
from aiogram.types import Message

from constants.commands import CommandText
from handlers.user.tools.day_schedule import send_day_schedule_message
from services.schedule.day_for_date import parse_dm_text

router = Router(name="user_day_schedule")

DATE_DM_TEXT_RE = r"^\s*\d{1,2}\.\d{1,2}\s*$"


@router.message(Command(CommandText.DAY))
async def day_command(message: Message, command: CommandObject) -> None:
    args = (command.args or "").strip()
    if not args:
        await message.answer(
            "Укажи дату: <code>/day 15.02</code> или одним сообщением <code>15.02</code>."
        )
        return
    if parse_dm_text(args) is None:
        await message.answer(
            "Формат даты: <code>ДД.ММ</code>, например <code>15.02</code>."
        )
        return
    await send_day_schedule_message(message, args)


@router.message(default_state, F.text.regexp(DATE_DM_TEXT_RE))
async def day_free_text_dm(message: Message) -> None:
    await send_day_schedule_message(message, message.text or "")
