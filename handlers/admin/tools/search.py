"""Запуск поиска пользователей и рендер результатов в одно сообщение."""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message
from tortoise.expressions import Q

from database.models import User
from keyboards.admin import SEARCH_BACK_FLT, search_results_kb

SEARCH_LIMIT = 25


async def run_search(query: str) -> tuple[list[User], int]:
    qs = User.filter(
        Q(username__icontains=query)
        | Q(tg_id__icontains=query)
        | Q(name__icontains=query)
        | Q(group_name__icontains=query)
    ).order_by("group_name", "name")
    total = await qs.count()
    users = await qs.limit(SEARCH_LIMIT)
    return users, total


def format_search_header(query: str, total: int) -> str:
    truncated = ""
    if total > SEARCH_LIMIT:
        truncated = f"\n(показаны первые {SEARCH_LIMIT} из {total})"
    return (
        f"🔍 Результаты по запросу <code>{query}</code>: "
        f"<b>{total}</b>{truncated}\n\nВыбери пользователя:"
    )


async def send_search_results(message: Message, query: str) -> bool:
    """Шлёт новое сообщение с результатами. ``True`` если что-то нашлось."""
    users, total = await run_search(query)
    if not users:
        return False
    await message.answer(
        format_search_header(query, total),
        reply_markup=search_results_kb(users, back_flt=SEARCH_BACK_FLT),
    )
    return True


async def edit_to_search_results(callback: CallbackQuery, query: str) -> bool:
    """Перерисовывает текущее сообщение в результаты поиска (для «назад»)."""
    users, total = await run_search(query)
    if not users:
        return False
    await callback.message.edit_text(
        format_search_header(query, total),
        reply_markup=search_results_kb(users, back_flt=SEARCH_BACK_FLT),
    )
    return True
