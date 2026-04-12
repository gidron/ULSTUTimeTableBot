from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery

from constants.callbacks import CallbackConstants
from constants.schedule_layout import ScheduleLayout, parse_schedule_layout
from database.models import User
from handlers.user.state_handlers.set_group_name import SET_GROUP_PROMPT
from handlers.user.state_handlers.teacher_schedule import (
    prompt_teacher_schedule,
)
from keyboards.inline import profile_inline_kb
from keyboards.factories import AcceptNewUserCallback
from keyboards.reply import cancel_kb
from handlers.user.state_handlers.contact_developer import prompt_contact_developer
from misc.states import SetGroupName, TeacherSchedule

router = Router(name="user_callbacks")


@router.callback_query(default_state, F.data == CallbackConstants.CONTACT_DEVELOPER)
async def contact_developer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await prompt_contact_developer(callback.message, state)


@router.callback_query(default_state, F.data == CallbackConstants.SET_GROUP_NAME)
async def set_group_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(SET_GROUP_PROMPT, reply_markup=cancel_kb)
    await state.set_state(SetGroupName.group_name)


@router.callback_query(default_state, F.data == CallbackConstants.TEACHER_SCHEDULE)
async def teacher_schedule_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await prompt_teacher_schedule(callback.message, state)


@router.callback_query(
    TeacherSchedule.teacher_query, F.data == CallbackConstants.TEACHER_SCHEDULE
)
async def teacher_schedule_repeat(callback: CallbackQuery, state: FSMContext):
    """Повторное нажатие кнопки в профиле во время ввода — обновляем подсказку."""
    await callback.answer()
    await prompt_teacher_schedule(callback.message, state)


@router.callback_query(default_state, F.data == CallbackConstants.TOGGLE_NOTIFICATIONS)
async def toggle_notifications(callback: CallbackQuery):
    user = await User.get(tg_id=callback.from_user.id)
    user.notify_by_change = not user.notify_by_change
    await user.save()

    toggle_text = "включены" if user.notify_by_change else "выключены"
    await callback.answer(f"Уведомления {toggle_text}")
    await callback.message.edit_reply_markup(
        reply_markup=profile_inline_kb(
            user.notify_by_change,
            parse_schedule_layout(user.schedule_layout),
        )
    )


@router.callback_query(
    default_state, F.data == CallbackConstants.TOGGLE_SCHEDULE_LAYOUT
)
async def toggle_schedule_layout(callback: CallbackQuery):
    user = await User.get(tg_id=callback.from_user.id)
    current = parse_schedule_layout(user.schedule_layout)
    user.schedule_layout = (
        ScheduleLayout.VERTICAL.value
        if current == ScheduleLayout.HORIZONTAL
        else ScheduleLayout.HORIZONTAL.value
    )
    await user.save()
    await callback.answer("Вид расписания сохранён")
    await callback.message.edit_reply_markup(
        reply_markup=profile_inline_kb(
            user.notify_by_change,
            parse_schedule_layout(user.schedule_layout),
        )
    )


@router.callback_query(default_state, AcceptNewUserCallback.filter())
async def accept_new_user(
    callback: CallbackQuery, callback_data: AcceptNewUserCallback
):
    tg_id = callback_data.tg_id
    is_accepted = callback_data.accept

    if is_accepted:
        user = await User.get(tg_id=tg_id)
        user.is_active = True
        await user.save()

        await callback.bot.send_sticker(
            chat_id=tg_id,
            sticker="CAACAgIAAxkBAAICFGnWk6zi3fLhHHqc5gxikWrEcmrKAAKcWwACl2dxSMeEVHqNXTnbOwQ",
        )
        await callback.bot.send_message(
            chat_id=tg_id, text="Тебя добавили. Введи /start"
        )

    await callback.answer("Успешно")
    await callback.message.edit_reply_markup(callback.inline_message_id, None)
    await callback.message.edit_text("✔ " + callback.message.text)
