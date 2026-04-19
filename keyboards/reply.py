from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

from constants.buttons_text import ButtonText as BT
from database.models import User

remove_kb = ReplyKeyboardRemove()


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard: list[list[KeyboardButton]] = [
        [KeyboardButton(text=BT.CURRENT_WEEK), KeyboardButton(text=BT.NEXT_WEEK)],
        [KeyboardButton(text=BT.PROFILE)],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=BT.ADMIN_PANEL_TITLE)])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Главное меню",
    )


async def main_menu_kb_for(tg_id: int | str) -> ReplyKeyboardMarkup:
    """Подгружает пользователя из БД и возвращает меню с учётом is_admin."""
    user = await User.get_or_none(tg_id=str(tg_id))
    return main_menu_kb(is_admin=bool(user and user.is_admin))


blocked_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BT.DEATH)]],
    resize_keyboard=True,
    input_field_placeholder="Ваш аккаунт заблокирован",
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BT.CANCEL)]], resize_keyboard=True
)
