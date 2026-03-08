from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.chat_action import ChatActionSender

from database.models import User
from keyboards.reply import main_menu_user_kb
from constants.buttons_text import ButtonText as BT
from misc.states import RegisterUserForm
from services.schedule_service import ScheduleService

router = Router(name="user_commands")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user = message.from_user
    tg_id = user.id
    full_name = user.full_name
    username = user.username

    user = await User.get_or_none(tg_id=tg_id)

    if user is None:
        user = await User.create(tg_id=tg_id, name=full_name, username=username, is_active=False)

    if user.is_active and not user.group_name:
        await message.answer(f'<b>{full_name}, добро пожаловать в нашего бота!</b>\n'
                             f'Перед тем как начать им пользоваться тебе необходимо '
                             f'указать группу, в которой ты учишься.\n'
                             f'Пример - <b>УИДбд-21</b>')
        await state.set_state(RegisterUserForm.group_name)
    elif user.is_active and user.group_name:
        await message.answer(f"С возвращением, <b>{full_name}</b>!", reply_markup=main_menu_user_kb)


@router.message(F.text == BT.CURRENT_WEEK)
@router.message(F.text == BT.NEXT_WEEK)
async def show_current_week(message: Message):
    tg_id = message.from_user.id
    user = await User.get(tg_id=tg_id)

    service = ScheduleService(user.group_name)
    message_to_delete = await message.answer("Твой запрос обрабатывается...")

    if message.text == BT.CURRENT_WEEK:
        week_kind = "current"
        caption = "Текущая неделя"
    else:
        week_kind = "next"
        caption = "Следующая неделя"

    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5):
        image_bytes, filename, week_range = await service.get_week_image(week_kind)
        caption = caption + " " + week_range if week_range else "Расписание недели"
        photo = BufferedInputFile(image_bytes, filename=filename)
        await message.answer_photo(photo=photo, caption=caption)

    await message_to_delete.delete()
