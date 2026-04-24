from datetime import date

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
from handlers.user.tools.day_schedule import resolve_day_schedule_outcome
from handlers.user.tools.profile_messages import (
    build_profile_group_page_text,
    build_profile_info_page_text,
    build_profile_root_text,
    build_profile_settings_page_text,
)
from keyboards.inline import (
    day_schedule_nav_kb,
    profile_group_schedule_inline_kb,
    profile_info_inline_kb,
    profile_root_inline_kb,
    profile_settings_inline_kb,
)
from keyboards.factories import AcceptNewUserCallback, DayScheduleNavCallback
from misc.user_welcome import notify_user_added
from services.network.university_client import UniversityClient
from services.schedule.day_for_date import (
    format_day_schedule_outcome_html,
    is_date_in_semester_window,
    schedule_today,
)
from services.schedule.day_schedule_session_cache import (
    get_day_schedule_session,
    save_day_schedule_session,
)
from keyboards.reply import cancel_kb
from handlers.user.state_handlers.contact_developer import prompt_contact_developer
from misc.states import DaySchedule, SetGroupName, TeacherSchedule

router = Router(name="user_callbacks")


@router.callback_query(default_state, DayScheduleNavCallback.filter())
async def day_schedule_pagination(
    callback: CallbackQuery, callback_data: DayScheduleNavCallback
) -> None:
    target_date = date(callback_data.y, callback_data.m, callback_data.d)
    ref_for_window = schedule_today()
    if not is_date_in_semester_window(target_date, ref_for_window):
        await callback.answer("Дата вне текущего семестра.", show_alert=True)
        return

    user = await User.get(tg_id=str(callback.from_user.id))
    if not user.group_name:
        await callback.answer("Сначала укажи группу в профиле.", show_alert=True)
        return

    await callback.answer()

    session = get_day_schedule_session(callback.from_user.id, user.group_name)
    if session is None:
        async with UniversityClient(group_name=user.group_name) as client:
            api_week, payload = await client.get_current_week_and_timetable()
        if api_week is None:
            await callback.message.edit_text(
                "Не удалось определить текущую учебную неделю. Попробуй позже."
            )
            return
        frozen = schedule_today()
        session = save_day_schedule_session(
            callback.from_user.id,
            user.group_name,
            api_current_week=api_week,
            payload=payload,
            frozen_today=frozen,
            anchor_date=target_date,
        )

    outcome = resolve_day_schedule_outcome(session, target_date)
    if outcome is None:
        await callback.message.edit_text(
            "Расписание на выбранный день пока недоступно.\n"
            "Попробуй позже ещё раз.",
            reply_markup=day_schedule_nav_kb(
                target_date, ref_today=session.frozen_today
            ),
        )
        return

    html_text = format_day_schedule_outcome_html(
        outcome,
        group_name=user.group_name,
        target_date=target_date,
    )
    nav = day_schedule_nav_kb(target_date, ref_today=session.frozen_today)
    await callback.message.edit_text(html_text, reply_markup=nav)


@router.callback_query(default_state, F.data == CallbackConstants.PROFILE_ROOT)
async def profile_open_root(callback: CallbackQuery):
    await callback.answer()
    user = await User.get(tg_id=str(callback.from_user.id))
    await callback.message.edit_text(
        build_profile_root_text(user),
        reply_markup=profile_root_inline_kb(),
    )


@router.callback_query(default_state, F.data == CallbackConstants.PROFILE_PAGE_GROUP)
async def profile_open_group_page(callback: CallbackQuery):
    await callback.answer()
    user = await User.get(tg_id=str(callback.from_user.id))
    await callback.message.edit_text(
        build_profile_group_page_text(user),
        reply_markup=profile_group_schedule_inline_kb(),
    )


@router.callback_query(default_state, F.data == CallbackConstants.PROFILE_PAGE_SETTINGS)
async def profile_open_settings_page(callback: CallbackQuery):
    await callback.answer()
    user = await User.get(tg_id=str(callback.from_user.id))
    await callback.message.edit_text(
        build_profile_settings_page_text(user),
        reply_markup=profile_settings_inline_kb(
            user.notify_by_change,
            parse_schedule_layout(user.schedule_layout),
        ),
    )


@router.callback_query(default_state, F.data == CallbackConstants.PROFILE_PAGE_INFO)
async def profile_open_info_page(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        build_profile_info_page_text(),
        reply_markup=profile_info_inline_kb(),
    )


DAY_SCHEDULE_PROMPT = (
    "Введи дату внутри текущего семестра (например <code>18.04</code>)."
)


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


@router.callback_query(default_state, F.data == CallbackConstants.SCHEDULE_BY_DATE)
async def schedule_by_date_entry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(DaySchedule.waiting_date)
    await callback.message.answer(DAY_SCHEDULE_PROMPT, reply_markup=cancel_kb)


@router.callback_query(
    DaySchedule.waiting_date, F.data == CallbackConstants.SCHEDULE_BY_DATE
)
async def schedule_by_date_repeat(callback: CallbackQuery, state: FSMContext):
    """Повторное нажатие кнопки во время ввода даты — обновляем подсказку."""
    await callback.answer()
    await callback.message.answer(DAY_SCHEDULE_PROMPT, reply_markup=cancel_kb)


@router.callback_query(
    TeacherSchedule.teacher_query, F.data == CallbackConstants.TEACHER_SCHEDULE
)
async def teacher_schedule_repeat(callback: CallbackQuery, state: FSMContext):
    """Повторное нажатие кнопки в профиле во время ввода — обновляем подсказку."""
    await callback.answer()
    await prompt_teacher_schedule(callback.message, state)


@router.callback_query(default_state, F.data == CallbackConstants.TOGGLE_NOTIFICATIONS)
async def toggle_notifications(callback: CallbackQuery):
    user = await User.get(tg_id=str(callback.from_user.id))
    user.notify_by_change = not user.notify_by_change
    await user.save()

    toggle_text = "включены" if user.notify_by_change else "выключены"
    await callback.answer(f"Уведомления {toggle_text}")
    await callback.message.edit_text(
        build_profile_settings_page_text(user),
        reply_markup=profile_settings_inline_kb(
            user.notify_by_change,
            parse_schedule_layout(user.schedule_layout),
        ),
    )


@router.callback_query(
    default_state, F.data == CallbackConstants.TOGGLE_SCHEDULE_LAYOUT
)
async def toggle_schedule_layout(callback: CallbackQuery):
    user = await User.get(tg_id=str(callback.from_user.id))
    current = parse_schedule_layout(user.schedule_layout)
    user.schedule_layout = (
        ScheduleLayout.VERTICAL.value
        if current == ScheduleLayout.HORIZONTAL
        else ScheduleLayout.HORIZONTAL.value
    )
    await user.save()
    await callback.answer("Вид расписания сохранён")
    await callback.message.edit_text(
        build_profile_settings_page_text(user),
        reply_markup=profile_settings_inline_kb(
            user.notify_by_change,
            parse_schedule_layout(user.schedule_layout),
        ),
    )


@router.callback_query(default_state, AcceptNewUserCallback.filter())
async def accept_new_user(
    callback: CallbackQuery, callback_data: AcceptNewUserCallback
):
    tg_id = callback_data.tg_id
    is_accepted = callback_data.accept

    if is_accepted:
        user = await User.get(tg_id=str(tg_id))
        user.is_active = True
        await user.save()

        await notify_user_added(callback.bot, tg_id)

    await callback.answer("Успешно")
    await callback.message.edit_reply_markup(callback.inline_message_id, None)
    await callback.message.edit_text("✔ " + callback.message.text)
