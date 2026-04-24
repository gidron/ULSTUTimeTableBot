"""Отправка расписания на конкретный день (парсинг ДД.ММ, API, HTML, кеш, навигация)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from database.models import User
from keyboards.inline import day_schedule_nav_kb
from keyboards.reply import main_menu_kb
from services.network.university_client import UniversityClient
from services.schedule.day_for_date import (
    DayScheduleSnapshot,
    build_day_schedule_snapshot,
    format_day_schedule_outcome_html,
    parse_dm_text,
    resolve_semester_calendar_date,
    schedule_today,
)
from services.schedule.day_schedule_session_cache import (
    DayScheduleSession,
    get_day_schedule_session,
    save_day_schedule_session,
)
from services.schedule.parser import TimetableParseError


def resolve_day_schedule_outcome(
    session: DayScheduleSession,
    target_date: date,
) -> DayScheduleSnapshot | Literal["sunday"] | None:
    if target_date in session.precomputed:
        return session.precomputed[target_date]
    try:
        return build_day_schedule_snapshot(
            target_date,
            api_current_week=session.api_current_week,
            payload=session.payload,
            group_name=session.group_name,
            today=session.frozen_today,
        )
    except TimetableParseError:
        return None


async def send_day_schedule_message(
    message: Message,
    raw_text: str,
    *,
    state: FSMContext | None = None,
) -> None:
    """Парсит «ДД.ММ», грузит API и шлёт HTML; сбрасывает ``state`` при переданном FSM."""
    tg_id = message.from_user.id
    user = await User.get(tg_id=str(tg_id))
    menu_kb = main_menu_kb(is_admin=user.is_admin)
    if not user.group_name:
        await message.answer(
            "Сначала укажи учебную группу в профиле.",
            reply_markup=menu_kb,
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
        await message.answer(str(exc), reply_markup=menu_kb)
        if state:
            await state.clear()
        return

    await message.answer("⏳ Расписание генерируется...", reply_markup=menu_kb)
    async with ChatActionSender(
        bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5
    ):
        async with UniversityClient(group_name=user.group_name) as client:
            api_week, payload = await client.get_current_week_and_timetable()

        if api_week is None:
            await message.answer(
                "Не удалось определить текущую учебную неделю. Попробуй позже.",
                reply_markup=menu_kb,
            )
        else:
            session = save_day_schedule_session(
                tg_id,
                user.group_name,
                api_current_week=api_week,
                payload=payload,
                frozen_today=today,
                anchor_date=target_date,
            )
            outcome = resolve_day_schedule_outcome(session, target_date)
            if outcome is None:
                await message.answer(
                    "Расписание на выбранный день пока недоступно.\n"
                    "Попробуй позже ещё раз.",
                    reply_markup=menu_kb,
                )
            else:
                html_text = format_day_schedule_outcome_html(
                    outcome,
                    group_name=user.group_name,
                    target_date=target_date,
                )
                nav = day_schedule_nav_kb(
                    target_date, ref_today=session.frozen_today
                )
                await message.answer(html_text, reply_markup=nav)

    if state:
        await state.clear()
