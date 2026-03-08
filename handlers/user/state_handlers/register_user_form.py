from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from database.models import User
from keyboards.reply import main_menu_user_kb
from misc.states import RegisterUserForm
from services.network import UniversityClient


router = Router(name="user_state_handlers_register_user_form")


@router.message(RegisterUserForm.group_name)
async def user_set_group_name(message: Message, state: FSMContext):
    user = message.from_user
    tg_id = user.id
    group_name = message.text

    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5):
        message_to_delete = await message.answer("Проверка корректности группы...")

        if not await UniversityClient(group_name).group_exists():
            await message.answer("Такой группы не найдено. Повторите попытку.")
            return

        await message_to_delete.delete()

    user = await User.get(tg_id=tg_id)
    user.group_name = group_name
    await user.save()

    await message.answer(
        'Группа сохранена! В дальнейшем ты сможешь изменить ее в настройках.',
            reply_markup=main_menu_user_kb
    )
    await state.set_state()


@router.message(RegisterUserForm.group_name, ~F.text)
async def invalid_user_set_group_name(message: Message):
    await message.answer("Укажи текстом!")
