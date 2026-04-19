from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from constants.buttons_text import ButtonText as BT
from constants.callbacks import CallbackConstants
from constants.schedule_layout import ScheduleLayout
from keyboards.factories import (
    DayScheduleNavCallback,
    PickSuggestedGroupCallback,
    PickSuggestedTeacherCallback,
)
from services.schedule.day_for_date import is_date_in_semester_window


def _schedule_layout_profile_label(layout: ScheduleLayout) -> str:
    if layout == ScheduleLayout.HORIZONTAL:
        return BT.SCHEDULE_LAYOUT_DAYS_ROWS
    return BT.SCHEDULE_LAYOUT_DAYS_COLUMNS


def _profile_back_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=BT.PROFILE_BACK, callback_data=CallbackConstants.PROFILE_ROOT
        )
    ]


def profile_root_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.PROFILE_PANEL_GROUP_SCHEDULE,
                    callback_data=CallbackConstants.PROFILE_PAGE_GROUP,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.PROFILE_PANEL_SETTINGS,
                    callback_data=CallbackConstants.PROFILE_PAGE_SETTINGS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.PROFILE_PANEL_INFO,
                    callback_data=CallbackConstants.PROFILE_PAGE_INFO,
                )
            ],
        ]
    )


def profile_group_schedule_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.CHANGE_GROUP,
                    callback_data=CallbackConstants.SET_GROUP_NAME,
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
                    text=BT.SCHEDULE_BY_DATE,
                    callback_data=CallbackConstants.SCHEDULE_BY_DATE,
                )
            ],
            _profile_back_row(),
        ]
    )


def profile_settings_inline_kb(
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
            _profile_back_row(),
        ]
    )


def profile_info_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.CONTACT_DEVELOPER,
                    callback_data=CallbackConstants.CONTACT_DEVELOPER,
                )
            ],
            _profile_back_row(),
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


def day_schedule_nav_kb(target_date: date, *, ref_today: date) -> InlineKeyboardMarkup:
    """Навигация ±1 день в границах семестра; подписи «◀ ДД.ММ» / «ДД.ММ ▶»."""
    row: list[InlineKeyboardButton] = []
    prev_d = target_date - timedelta(days=1)
    if is_date_in_semester_window(prev_d, ref_today):
        dm = prev_d.strftime("%d.%m")
        row.append(
            InlineKeyboardButton(
                text=f"◀ {dm}",
                callback_data=DayScheduleNavCallback(
                    y=prev_d.year, m=prev_d.month, d=prev_d.day
                ).pack(),
            )
        )
    next_d = target_date + timedelta(days=1)
    if is_date_in_semester_window(next_d, ref_today):
        dm = next_d.strftime("%d.%m")
        row.append(
            InlineKeyboardButton(
                text=f"{dm} ▶",
                callback_data=DayScheduleNavCallback(
                    y=next_d.year, m=next_d.month, d=next_d.day
                ).pack(),
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])


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
