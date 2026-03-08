from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Текущая неделя", callback_data="week:current"),
                InlineKeyboardButton(text="Следующая неделя", callback_data="week:next"),
            ]
        ]
    )
