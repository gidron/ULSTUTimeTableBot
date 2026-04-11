from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from constants.buttons_text import ButtonText as BT
from constants.callbacks import CallbackConstants
from keyboards.factories import PickSuggestedGroupCallback, PickSuggestedTeacherCallback


def profile_inline_kb(notifications_enabled: bool) -> InlineKeyboardMarkup:
    notifications_button_text = (
        BT.DISABLE_NOTIFICATIONS if notifications_enabled else BT.ENABLE_NOTIFICATIONS
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.CHANGE_GROUP, callback_data=CallbackConstants.SET_GROUP_NAME
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.TEACHER_SCHEDULE,
                    callback_data=CallbackConstants.TEACHER_SCHEDULE,
                )
            ],
            [
                InlineKeyboardButton(
                    text=notifications_button_text,
                    callback_data=CallbackConstants.TOGGLE_NOTIFICATIONS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.CONTACT_DEVELOPER,
                    callback_data=CallbackConstants.CONTACT_DEVELOPER,
                )
            ],
        ]
    )


def teacher_suggestions_inline_kb(teachers: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i, name in enumerate(teachers):
        label = name if len(name) <= 64 else f"{name[:61]}..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=PickSuggestedTeacherCallback(index=i).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def group_suggestions_inline_kb(groups: list[str]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i, name in enumerate(groups):
        label = name if len(name) <= 64 else f"{name[:61]}..."
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=PickSuggestedGroupCallback(index=i).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
