from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from constants.buttons_text import ButtonText as BT
from handlers.admin.tools import search_cache
from handlers.admin.tools.search import send_search_results
from handlers.admin.tools.texts import build_menu_text
from keyboards.admin import admin_menu_kb
from keyboards.reply import main_menu_kb
from misc.filters import IsAdminUser
from misc.states import AdminSearch

router = Router(name="admin_state_search")
router.message.filter(IsAdminUser())


async def _exit_to_menu(message: Message, state: FSMContext, *, header: str) -> None:
    await state.set_state()
    await message.answer(header, reply_markup=main_menu_kb(is_admin=True))
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

    await state.set_state()
    found = await send_search_results(message, query)
    if not found:
        search_cache.clear(message.from_user.id)
        await _exit_to_menu(
            message,
            state,
            header=f"По запросу <code>{query}</code> ничего не найдено.",
        )
        return

    search_cache.remember(message.from_user.id, query)
    await message.answer(
        "Готово. Открой пользователя из списка выше или вернись в меню.",
        reply_markup=main_menu_kb(is_admin=True),
    )
