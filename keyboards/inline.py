from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants.buttons_text import ButtonText as BT
from constants.callbacks import CallbackConstants


def profile_inline_kb(notifications_enabled: bool) -> InlineKeyboardMarkup:
    notifications_button_text = (
        BT.DISABLE_NOTIFICATIONS if notifications_enabled else BT.ENABLE_NOTIFICATIONS
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.CHANGE_GROUP,
                    callback_data=CallbackConstants.SET_GROUP_NAME
                )
            ],
            [
                InlineKeyboardButton(
                    text=notifications_button_text,
                    callback_data=CallbackConstants.TOGGLE_NOTIFICATIONS
                )
            ],
        ]
    )
