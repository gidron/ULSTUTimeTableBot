from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from constants.buttons_text import ButtonText as BT
from constants.callbacks import CallbackConstants
from constants.schedule_layout import ScheduleLayout
from keyboards.factories import PickSuggestedGroupCallback, PickSuggestedTeacherCallback


def _schedule_layout_profile_label(layout: ScheduleLayout) -> str:
    if layout == ScheduleLayout.HORIZONTAL:
        return "📅 Вид: дни строками"
    return "📅 Вид: дни столбцами"


def profile_inline_kb(
    notifications_enabled: bool,
    schedule_layout: ScheduleLayout = ScheduleLayout.HORIZONTAL,
) -> InlineKeyboardMarkup:
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
                    text=_schedule_layout_profile_label(schedule_layout),
                    callback_data=CallbackConstants.TOGGLE_SCHEDULE_LAYOUT,
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
