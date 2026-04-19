from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from core.config import get_settings
from database.models import User
from keyboards.reply import cancel_kb, main_menu_kb, main_menu_kb_for
from misc.states import ContactDeveloper
from misc.user_admin_card import format_user_admin_card_html
from constants.buttons_text import ButtonText as BT

router = Router(name="user_state_handlers_contact_developer")

CONTACT_PROMPT = (
    "Напиши одним сообщением вопрос или обращение разработчику — "
    "можно текст, фото, файл или голосовое. "
)


async def prompt_contact_developer(message: Message, state: FSMContext) -> None:
    await state.set_state(ContactDeveloper.message)
    await message.answer(CONTACT_PROMPT, reply_markup=cancel_kb)


@router.message(ContactDeveloper.message, Command("cancel"))
@router.message(ContactDeveloper.message, F.text == BT.CANCEL)
async def cancel_contact(message: Message, state: FSMContext):
    await message.answer(
        "Отменено.", reply_markup=await main_menu_kb_for(message.from_user.id)
    )
    await state.set_state()


@router.message(ContactDeveloper.message, F.text.startswith("/"))
async def contact_ignore_commands(message: Message):
    await message.answer(
        "Сейчас ожидается сообщение для разработчика. Отправь его или нажми «Отмена»."
    )


@router.message(ContactDeveloper.message)
async def send_contact_to_developer(message: Message, state: FSMContext):
    settings = get_settings()
    db_user = await User.get(tg_id=message.from_user.id)
    fu = message.from_user

    header = format_user_admin_card_html(
        title="Сообщение пользователя",
        tg_id=fu.id,
        full_name=fu.full_name,
        username=fu.username,
        group_name=db_user.group_name,
    )
    await message.bot.send_message(
        chat_id=settings.developer_chat_id,
        text=header,
    )
    await message.bot.copy_message(
        chat_id=settings.developer_chat_id,
        from_chat_id=message.chat.id,
        message_id=message.message_id,
    )

    await message.answer(
        "Сообщение отправлено разработчику. Спасибо!",
        reply_markup=main_menu_kb(is_admin=db_user.is_admin),
    )
    await state.set_state()
