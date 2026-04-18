from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from tortoise.expressions import Q

from constants.buttons_text import ButtonText as BT
from database.models import User
from handlers.admin.tools.texts import build_menu_text
from keyboards.admin import admin_menu_kb, search_results_kb
from keyboards.reply import main_menu_user_kb
from misc.filters import IsAdminUser
from misc.states import AdminSearch

router = Router(name="admin_state_search")
router.message.filter(IsAdminUser())

SEARCH_LIMIT = 25


async def _exit_to_menu(message: Message, state: FSMContext, *, header: str) -> None:
    await state.set_state()
    await message.answer(header, reply_markup=main_menu_user_kb)
    await message.answer(build_menu_text(), reply_markup=admin_menu_kb())


@router.message(AdminSearch.query, Command("cancel"))
@router.message(AdminSearch.query, F.text == BT.CANCEL)
async def cancel_search(message: Message, state: FSMContext) -> None:
    await _exit_to_menu(message, state, header="Поиск отменён.")


@router.message(AdminSearch.query)
async def handle_search(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    if not query:
        await message.answer("Пустой запрос. Попробуй ещё раз.")
        return

    qs = User.filter(
        Q(username__icontains=query)
        | Q(tg_id__icontains=query)
        | Q(name__icontains=query)
        | Q(group_name__icontains=query)
    ).order_by("group_name", "name")

    total = await qs.count()
    users = await qs.limit(SEARCH_LIMIT)
    await state.set_state()

    if not users:
        await _exit_to_menu(
            message,
            state,
            header=f"По запросу <code>{query}</code> ничего не найдено.",
        )
        return

    truncated = ""
    if total > SEARCH_LIMIT:
        truncated = f"\n(показаны первые {SEARCH_LIMIT} из {total})"

    await message.answer(
        f"🔍 Результаты по запросу <code>{query}</code>: <b>{total}</b>{truncated}",
        reply_markup=main_menu_user_kb,
    )
    await message.answer(
        "Выбери пользователя:",
        reply_markup=search_results_kb(users),
    )
