from constants.buttons_text import ButtonText as BT
from aiogram.types import InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.factories import AcceptNewUserCallback


def accept_new_user_kb(tg_id: int):
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(
            text=BT.ACCEPT_USER,
            callback_data=AcceptNewUserCallback(
                tg_id=tg_id,
                accept=True
            ).pack()
        ),
        InlineKeyboardButton(
            text=BT.CANCEL_USER,
            callback_data=AcceptNewUserCallback(
                tg_id=tg_id,
                accept=False
            ).pack()
        )
    )

    return keyboard.adjust(2).as_markup()
