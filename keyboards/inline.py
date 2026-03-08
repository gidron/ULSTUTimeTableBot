from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants.buttons_text import ButtonText as BT
from constants.callbacks import CallbackConstants


profile_inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=BT.CHANGE_GROUP,
                callback_data=CallbackConstants.SET_GROUP_NAME
            )
        ]
    ]
)
