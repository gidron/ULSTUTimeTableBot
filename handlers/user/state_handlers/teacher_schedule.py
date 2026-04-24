from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from constants.buttons_text import ButtonText as BT
from constants.schedule_layout import parse_schedule_layout
from database.models import User
from keyboards.factories import PickSuggestedTeacherCallback
from keyboards.inline import teacher_suggestions_inline_kb
from keyboards.reply import cancel_kb, main_menu_kb
from misc.states import TeacherSchedule
from services.network.university_client import UniversityClient
from services.schedule.service import ScheduleService
from services.schedule.parser import TimetableParseError

router = Router(name="user_state_handlers_teacher_schedule")

SET_TEACHER_PROMPT = (
    "Введи фамилия или инициалы преподавателя\n"
    "Пример - <code>Волкова</code> или <code>Волкова Е А</code> "
)

SCHEDULE_PREFIX_TEACHER = "Расписание преподавателя:"


async def prompt_teacher_schedule(message: Message, state: FSMContext) -> None:
    await state.set_state(TeacherSchedule.teacher_query)
    await message.answer(SET_TEACHER_PROMPT, reply_markup=cancel_kb)


async def _complete_teacher_schedule(
    message: Message,
    teacher_name: str,
    state: FSMContext,
    *,
    user_tg_id: int | None = None,
) -> None:
    await state.update_data(suggested_teachers=None)
    await state.set_state()

    tg_id = user_tg_id if user_tg_id is not None else message.from_user.id
    user = await User.get(tg_id=str(tg_id))
    layout = parse_schedule_layout(user.schedule_layout)
    menu_kb = main_menu_kb(is_admin=user.is_admin)

    service = ScheduleService(
        teacher_name,
        schedule_title_prefix=SCHEDULE_PREFIX_TEACHER,
        include_study_group_in_slots=True,
    )
    message_to_delete = await message.answer("⏳ Расписание генерируется...")

    loaded: list[tuple[str, bytes, str, str, str]] = []
    async with ChatActionSender(
        bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5
    ):
        for week_kind, week_caption in (
            ("current", "Текущая неделя"),
            ("next", "Следующая неделя"),
        ):
            try:
                image_bytes, filename, week_range = await service.get_week_image(
                    week_kind, layout=layout
                )
            except TimetableParseError:
                await message.answer(
                    f"Расписание на <b>{week_caption.lower()}</b> пока недоступно."
                )
            else:
                loaded.append(
                    (week_kind, image_bytes, filename, week_range, week_caption)
                )

    await message_to_delete.delete()

    if not loaded:
        await message.answer(
            "Не удалось загрузить расписание. Попробуй позже.",
            reply_markup=menu_kb,
        )
        return

    for i, (_, image_bytes, filename, week_range, week_caption) in enumerate(loaded):
        is_last = i == len(loaded) - 1
        caption = (
            f"📚 Расписание для преподавателя <b>{teacher_name}</b>\n"
            f"🕰️ {week_caption} <b>{week_range}</b>"
            if week_range
            else (
                f"📚 Расписание для преподавателя <b>{teacher_name}</b>\n"
                f"🕰️ {week_caption}"
            )
        )
        photo = BufferedInputFile(image_bytes, filename=filename)
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=menu_kb if is_last else None,
        )


@router.message(TeacherSchedule.teacher_query, F.text == BT.CANCEL)
async def cancel_teacher_input(message: Message, state: FSMContext):
    await state.update_data(suggested_teachers=None)
    user = await User.get(tg_id=str(message.from_user.id))
    await message.answer(
        "Отменено", reply_markup=main_menu_kb(is_admin=user.is_admin)
    )
    await state.set_state()


@router.callback_query(
    TeacherSchedule.teacher_query, PickSuggestedTeacherCallback.filter()
)
async def pick_suggested_teacher(
    callback: CallbackQuery,
    callback_data: PickSuggestedTeacherCallback,
    state: FSMContext,
):
    data = await state.get_data()
    teachers: list[str] = data.get("suggested_teachers") or []
    idx = callback_data.index
    if idx < 0 or idx >= len(teachers):
        await callback.answer(
            "Список устарел. Введи запрос ещё раз (фамилию, инициалы или вместе).",
            show_alert=True,
        )
        return

    await callback.answer()
    teacher_name = teachers[idx]
    await callback.message.delete()
    await _complete_teacher_schedule(
        callback.message,
        teacher_name,
        state,
        user_tg_id=callback.from_user.id,
    )


@router.message(TeacherSchedule.teacher_query, F.text)
async def user_enter_teacher_query(message: Message, state: FSMContext):
    query = message.text.strip()

    if len(query) < 3:
        await message.answer(
            "Запрос должен быть не короче 3 символов.",
        )
        return

    async with ChatActionSender(
        bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5
    ):
        message_to_delete = await message.answer("🔍 Ищем преподавателя...")

        async with UniversityClient(query) as client:
            teachers = await client.find_teachers()

            if query not in teachers:
                await message_to_delete.delete()
                if not teachers:
                    await message.answer(
                        "Такого преподавателя не найдено. Попробуй другое написание "
                        "(не короче 3 символов)."
                    )
                    return

                await state.update_data(suggested_teachers=teachers)
                await message.answer(
                    "Точного совпадения нет. Выбери одного из найденных:",
                    reply_markup=teacher_suggestions_inline_kb(teachers),
                )
                return

        await message_to_delete.delete()

    await state.update_data(suggested_teachers=None)
    await _complete_teacher_schedule(message, query, state)


@router.message(TeacherSchedule.teacher_query, ~F.text)
async def invalid_teacher_input(message: Message):
    await message.answer("Введи текст!")
