from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from constants.buttons_text import ButtonText as BT
from database.models import User
from keyboards.factories import (
    AdminActionCallback,
    AdminListCallback,
    AdminMenuCallback,
    AdminUserCallback,
)


PAGE_SIZE = 8

FILTER_LABELS: dict[str, str] = {
    "all": BT.ADMIN_FILTER_ALL,
    "active": BT.ADMIN_FILTER_ACTIVE,
    "banned": BT.ADMIN_FILTER_BANNED,
    "admins": BT.ADMIN_FILTER_ADMINS,
    "nogroup": BT.ADMIN_FILTER_NOGROUP,
}

FILTER_ORDER: tuple[str, ...] = ("all", "active", "banned", "admins", "nogroup")

SORT_NAME = "name"
SORT_SEEN = "seen"
SORT_LABELS: dict[str, str] = {
    SORT_NAME: BT.ADMIN_SORT_LABEL_NAME,
    SORT_SEEN: BT.ADMIN_SORT_LABEL_SEEN,
}

# Маркер "вернуться к результатам поиска" вместо обычного списка.
SEARCH_BACK_FLT = "_search"


def _back_to_origin_button(
    *, back_flt: str, back_page: int, back_sort: str
) -> InlineKeyboardButton:
    """Кнопка «назад» к списку или к результатам поиска."""
    if back_flt == SEARCH_BACK_FLT:
        return InlineKeyboardButton(
            text=BT.ADMIN_BACK_SEARCH,
            callback_data=AdminListCallback(
                flt=SEARCH_BACK_FLT, page=0, sort=back_sort
            ).pack(),
        )
    return InlineKeyboardButton(
        text=BT.ADMIN_BACK_LIST,
        callback_data=AdminListCallback(
            flt=back_flt, page=back_page, sort=back_sort
        ).pack(),
    )


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_MENU_STATS,
                    callback_data=AdminMenuCallback(page="stats").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_MENU_USERS,
                    callback_data=AdminListCallback(flt="all", page=0).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_MENU_SEARCH,
                    callback_data=AdminMenuCallback(page="search").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_MENU_BROADCAST,
                    callback_data=AdminMenuCallback(page="bcast").pack(),
                )
            ],
        ]
    )


def admin_back_to_menu_row() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=BT.ADMIN_BACK_MENU,
            callback_data=AdminMenuCallback(page="root").pack(),
        )
    ]


def stats_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[admin_back_to_menu_row()])


def search_prompt_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[admin_back_to_menu_row()])


def broadcast_hint_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[admin_back_to_menu_row()])


def _format_seen_short(user: User) -> str:
    if user.last_day_online is None:
        return "—"
    d = user.last_day_online
    return f"{d.day:02d}.{d.month:02d}"


def _user_row_label(user: User, *, sort: str = SORT_NAME) -> str:
    flags: list[str] = []
    if user.is_admin:
        flags.append("💀")
    flags.append("✔" if user.is_active else "❌")
    flag_str = "".join(flags)
    group = user.group_name or "—"
    if sort == SORT_SEEN:
        label = f"{flag_str} {_format_seen_short(user)} · {group} · {user.name}"
    else:
        label = f"{flag_str} {group} · {user.name}"
    if len(label) > 64:
        label = label[:61] + "..."
    return label


def _sort_toggle_row(filter_key: str, sort: str) -> list[InlineKeyboardButton]:
    next_sort = SORT_SEEN if sort == SORT_NAME else SORT_NAME
    label = BT.ADMIN_SORT_BY_SEEN if next_sort == SORT_SEEN else BT.ADMIN_SORT_BY_NAME
    return [
        InlineKeyboardButton(
            text=label,
            callback_data=AdminListCallback(
                flt=filter_key, page=0, sort=next_sort
            ).pack(),
        )
    ]


def users_list_kb(
    users: list[User],
    *,
    filter_key: str,
    page: int,
    total_pages: int,
    sort: str = SORT_NAME,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_user_row_label(user, sort=sort),
                    callback_data=AdminUserCallback(
                        tg_id=int(user.tg_id),
                        back_flt=filter_key,
                        back_page=page,
                        back_sort=sort,
                    ).pack(),
                )
            ]
        )

    filter_row: list[InlineKeyboardButton] = []
    for key in FILTER_ORDER:
        label = FILTER_LABELS[key]
        if key == filter_key:
            label = f"• {label} •"
        filter_row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=AdminListCallback(flt=key, page=0, sort=sort).pack(),
            )
        )
    rows.append(filter_row[:3])
    if len(filter_row) > 3:
        rows.append(filter_row[3:])

    rows.append(_sort_toggle_row(filter_key, sort))

    nav_row: list[InlineKeyboardButton] = []
    has_prev = page > 0
    has_next = page < max(total_pages - 1, 0)
    if has_prev:
        nav_row.append(
            InlineKeyboardButton(
                text=BT.ADMIN_PAGE_PREV,
                callback_data=AdminListCallback(
                    flt=filter_key, page=page - 1, sort=sort
                ).pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{max(total_pages, 1)}",
            callback_data=AdminListCallback(
                flt=filter_key, page=page, sort=sort
            ).pack(),
        )
    )
    if has_next:
        nav_row.append(
            InlineKeyboardButton(
                text=BT.ADMIN_PAGE_NEXT,
                callback_data=AdminListCallback(
                    flt=filter_key, page=page + 1, sort=sort
                ).pack(),
            )
        )
    rows.append(nav_row)

    rows.append(admin_back_to_menu_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def search_results_kb(
    users: list[User],
    *,
    back_flt: str = "all",
    back_page: int = 0,
    back_sort: str = SORT_NAME,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_user_row_label(user, sort=back_sort),
                    callback_data=AdminUserCallback(
                        tg_id=int(user.tg_id),
                        back_flt=back_flt,
                        back_page=back_page,
                        back_sort=back_sort,
                    ).pack(),
                )
            ]
        )
    rows.append(admin_back_to_menu_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def user_card_kb(
    user: User,
    *,
    actor_tg_id: int,
    back_flt: str,
    back_page: int,
    back_sort: str = SORT_NAME,
) -> InlineKeyboardMarkup:
    is_self = int(user.tg_id) == int(actor_tg_id)
    rows: list[list[InlineKeyboardButton]] = []

    ban_label = BT.ADMIN_ACT_UNBAN if not user.is_active else BT.ADMIN_ACT_BAN
    admin_label = (
        BT.ADMIN_ACT_DROP_ADMIN if user.is_admin else BT.ADMIN_ACT_MAKE_ADMIN
    )

    def _action(action: str) -> str:
        return AdminActionCallback(
            tg_id=int(user.tg_id),
            action=action,
            back_flt=back_flt,
            back_page=back_page,
            back_sort=back_sort,
        ).pack()

    toggle_row: list[InlineKeyboardButton] = []
    if not is_self:
        toggle_row.append(
            InlineKeyboardButton(text=ban_label, callback_data=_action("ban"))
        )
    if not (is_self and user.is_admin):
        toggle_row.append(
            InlineKeyboardButton(text=admin_label, callback_data=_action("admin"))
        )
    if toggle_row:
        rows.append(toggle_row)

    rows.append(
        [InlineKeyboardButton(text=BT.ADMIN_ACT_DM, callback_data=_action("dm"))]
    )

    if not is_self:
        rows.append(
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_ACT_DELETE, callback_data=_action("delete")
                )
            ]
        )

    rows.extend(
        [
            [
            _back_to_origin_button(
                back_flt=back_flt, back_page=back_page, back_sort=back_sort
            ),
            ],
            [
            InlineKeyboardButton(
                text=BT.ADMIN_BACK_MENU,
                callback_data=AdminMenuCallback(page="root").pack(),
            ),
            ]
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_confirm_kb(
    user: User,
    *,
    back_flt: str,
    back_page: int,
    back_sort: str = SORT_NAME,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_ACT_DELETE_CONFIRM,
                    callback_data=AdminActionCallback(
                        tg_id=int(user.tg_id),
                        action="delete_confirm",
                        back_flt=back_flt,
                        back_page=back_page,
                        back_sort=back_sort,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_ACT_DELETE_CANCEL,
                    callback_data=AdminActionCallback(
                        tg_id=int(user.tg_id),
                        action="delete_cancel",
                        back_flt=back_flt,
                        back_page=back_page,
                        back_sort=back_sort,
                    ).pack(),
                )
            ],
        ]
    )


def dm_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BT.ADMIN_ACT_DELETE_CANCEL,
                    callback_data=AdminMenuCallback(page="root").pack(),
                )
            ]
        ]
    )


def post_delete_nav_kb(
    *, back_flt: str, back_page: int, back_sort: str = SORT_NAME
) -> InlineKeyboardMarkup:
    """Подвал-навигация после удаления пользователя (карточки уже нет)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _back_to_origin_button(
                    back_flt=back_flt, back_page=back_page, back_sort=back_sort
                ),
                InlineKeyboardButton(
                    text=BT.ADMIN_BACK_MENU,
                    callback_data=AdminMenuCallback(page="root").pack(),
                ),
            ]
        ]
    )
