"""FSM: ввод даты после кнопки «Расписание на день» в профиле."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from constants.buttons_text import ButtonText as BT
from handlers.user.day_schedule import send_day_schedule_message
from keyboards.reply import main_menu_user_kb
from misc.states import DaySchedule
from services.schedule.day_for_date import parse_dm_text

router = Router(name="user_state_handlers_day_schedule")


@router.message(DaySchedule.waiting_date, F.text == BT.CANCEL)
async def day_schedule_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_menu_user_kb)


@router.message(DaySchedule.waiting_date, F.text)
async def day_schedule_waiting(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if parse_dm_text(text) is None:
        await message.answer(
            "Нужен формат <code>ДД.ММ</code>, например <code>15.02</code>."
        )
        return
    await send_day_schedule_message(message, text, state=state)
