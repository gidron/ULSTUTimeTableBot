from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from constants.buttons_text import ButtonText as BT


main_menu_user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=BT.CURRENT_WEEK),
            KeyboardButton(text=BT.NEXT_WEEK)
        ],
        [
            KeyboardButton(text=BT.PROFILE)
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Главное меню"
)

blocked_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text=BT.DEATH)
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="Ваш аккаунт заблокирован"
)
