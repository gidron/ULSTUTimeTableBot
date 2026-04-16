"""Команда /day, свободный текст «ДД.ММ» (вне FSM ожидания даты)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from constants.commands import CommandText
from database.models import User
from keyboards.reply import main_menu_user_kb
from services.network.university_client import UniversityClient
from services.schedule.day_for_date import (
    build_day_schedule_snapshot,
    format_day_schedule_html,
    parse_dm_text,
    resolve_semester_calendar_date,
    schedule_today,
)
from services.schedule.parser import TimetableParseError

router = Router(name="user_day_schedule")

DATE_DM_TEXT_RE = r"^\s*\d{1,2}\.\d{1,2}\s*$"


async def send_day_schedule_message(
    message: Message,
    raw_text: str,
    *,
    state: FSMContext | None = None,
) -> None:
    """Парсит «ДД.ММ», грузит API и шлёт HTML; сбрасывает ``state`` при переданном FSM."""
    tg_id = message.from_user.id
    user = await User.get(tg_id=tg_id)
    if not user.group_name:
        await message.answer(
            "Сначала укажи учебную группу в профиле.",
            reply_markup=main_menu_user_kb,
        )
        if state:
            await state.clear()
        return

    parsed_dm = parse_dm_text(raw_text)
    if parsed_dm is None:
        await message.answer(
            "Нужен формат <code>ДД.ММ</code>, например <code>15.02</code>."
        )
        if state:
            await state.clear()
        return

    day, month = parsed_dm
    try:
        today = schedule_today()
        target_date = resolve_semester_calendar_date(day, month, today)
    except ValueError as exc:
        await message.answer(str(exc), reply_markup=main_menu_user_kb)
        if state:
            await state.clear()
        return

    message_to_delete = await message.answer("⏳ Расписание генерируется...")
    try:
        async with ChatActionSender(
            bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5
        ):
            async with UniversityClient(group_name=user.group_name) as client:
                api_week, payload = await client.get_current_week_and_timetable()

            if api_week is None:
                await message.answer(
                    "Не удалось определить текущую учебную неделю. Попробуй позже.",
                    reply_markup=main_menu_user_kb,
                )
            else:
                try:
                    outcome = build_day_schedule_snapshot(
                        target_date,
                        api_current_week=api_week,
                        payload=payload,
                        group_name=user.group_name,
                        today=today,
                    )
                except TimetableParseError:
                    await message.answer(
                        "Расписание на выбранный день пока недоступно.\n"
                        "Попробуй позже ещё раз.",
                        reply_markup=main_menu_user_kb,
                    )
                else:
                    if outcome == "sunday":
                        await message.answer(
                            "В расписании учитываются только дни с понедельника по субботу.",
                            reply_markup=main_menu_user_kb,
                        )
                    else:
                        html_text = format_day_schedule_html(outcome)
                        await message.answer(
                            html_text, reply_markup=main_menu_user_kb
                        )
    finally:
        await message_to_delete.delete()

    if state:
        await state.clear()


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
