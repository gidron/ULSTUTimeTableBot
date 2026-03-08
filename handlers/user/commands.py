from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.chat_action import ChatActionSender

from keyboards.reply import main_menu_user_kb
from constants.buttons_text import ButtonText as BT
from services.schedule_service import ScheduleService

router = Router(name="user_commands")
service = ScheduleService()


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Привет. Нажми кнопку ниже, чтобы получить расписание картинкой.",
        reply_markup=main_menu_user_kb,
    )


@router.message(F.text == BT.CURRENT_WEEK)
async def show_current_week(message: Message):
    message_to_delete = await message.answer("Подождите ..")

    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5):
        image_bytes, filename = await service.get_week_image("current")
        photo = BufferedInputFile(image_bytes, filename=filename)
        await message.answer_photo(photo=photo, caption="Текущая неделя")

    await message_to_delete.delete()


@router.message(F.text == BT.NEXT_WEEK)
async def show_current_week(message: Message):
    message_to_delete = await message.answer("Подождите ..")

    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5):
        image_bytes, filename = await service.get_week_image("next")
        photo = BufferedInputFile(image_bytes, filename=filename)
        await message.answer_photo(photo=photo, caption="Текущая неделя")

    await message_to_delete.delete()
