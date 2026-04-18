"""Текстовые билдеры для всех экранов админ-панели."""

from __future__ import annotations

from collections import Counter

from constants.buttons_text import ButtonText as BT
from constants.schedule_layout import parse_schedule_layout
from database.models import User
from keyboards.admin import FILTER_LABELS

SEARCH_PROMPT = (
    "<b>🔍 Поиск пользователя</b>\n\n"
    "Отправь часть <b>username</b>, <b>tg_id</b>, <b>имени</b> или <b>группы</b>."
)

BROADCAST_HINT = (
    "<b>📣 Рассылка</b>\n\n"
    "Чтобы разослать сообщение всем активным пользователям — ответь "
    "командой <code>/broadcast</code> на нужное сообщение."
)


def build_menu_text() -> str:
    return (
        f"<b>{BT.ADMIN_PANEL_TITLE}</b>\n\n"
        "Выбери раздел ниже:\n"
        f"• {BT.ADMIN_MENU_STATS} — общая сводка\n"
        f"• {BT.ADMIN_MENU_USERS} — список и фильтры\n"
        f"• {BT.ADMIN_MENU_SEARCH} — поиск по username/tg_id/группе/имени\n"
        f"• {BT.ADMIN_MENU_BROADCAST} — массовая рассылка"
    )


async def build_stats_text() -> str:
    total = await User.all().count()
    active = await User.filter(is_active=True).count()
    banned = await User.filter(is_active=False).count()
    admins = await User.filter(is_admin=True).count()
    nogroup = await User.filter(group_name__isnull=True).count()

    groups: list[str | None] = await User.all().values_list("group_name", flat=True)
    counter = Counter(g for g in groups if g)
    top = counter.most_common(10)

    lines = [
        f"<b>{BT.ADMIN_MENU_STATS}</b>",
        "",
        f"Всего: <b>{total}</b>",
        f"Активных: <b>{active}</b>",
        f"Забаненных: <b>{banned}</b>",
        f"Админов: <b>{admins}</b>",
        f"Без группы: <b>{nogroup}</b>",
    ]
    if top:
        lines.append("")
        lines.append("<b>Топ групп:</b>")
        for name, count in top:
            lines.append(f"• <code>{name}</code> — {count}")
    return "\n".join(lines)


def build_list_text(filter_key: str, total: int, page: int, total_pages: int) -> str:
    label = FILTER_LABELS.get(filter_key, filter_key)
    return (
        f"<b>{BT.ADMIN_MENU_USERS}</b>\n"
        f"Фильтр: <b>{label}</b>\n"
        f"Найдено: <b>{total}</b>\n"
        f"Страница: <b>{min(page + 1, max(total_pages, 1))}/{max(total_pages, 1)}</b>"
    )


def _bool_label(value: bool) -> str:
    return "✅" if value else "❌"


def build_user_card_text(user: User, *, header: str | None = None) -> str:
    username = f"@{user.username}" if user.username else "—"
    layout = parse_schedule_layout(user.schedule_layout).value
    last_seen = user.last_day_online.isoformat() if user.last_day_online else "—"
    title = header or "<b>👤 Карточка пользователя</b>"
    lines = [
        title,
        "",
        f"ID: <code>{user.tg_id}</code>",
        f"Имя: <b>{user.name}</b>",
        f"Username: {username}",
        f"Группа: <b>{user.group_name or '—'}</b>",
        "",
        f"Активен: {_bool_label(user.is_active)}",
        f"Админ: {_bool_label(user.is_admin)}",
        f"Уведомления: {_bool_label(user.notify_by_change)}",
        f"Раскладка: <code>{layout}</code>",
        f"Последний онлайн: <code>{last_seen}</code>",
    ]
    return "\n".join(lines)


def build_delete_confirm_text(user: User) -> str:
    return build_user_card_text(
        user,
        header="<b>⚠️ Удалить пользователя?</b>\nЭто действие необратимо.",
    )


def build_dm_prompt_text(user: User) -> str:
    return (
        f"<b>✉️ Сообщение пользователю</b>\n"
        f"Получатель: <code>{user.tg_id}</code> ({user.name})\n\n"
        "Отправь текст или медиа одним сообщением — оно будет скопировано "
        "в личку пользователю от имени бота."
    )
