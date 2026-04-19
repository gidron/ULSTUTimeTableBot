from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from constants.buttons_text import ButtonText as BT
from handlers.admin.tools.texts import build_menu_text
from keyboards.admin import admin_menu_kb
from keyboards.reply import main_menu_kb
from misc.admin_audit import log_admin_action
from misc.filters import IsAdminUser
from misc.states import AdminDM

router = Router(name="admin_state_dm")
router.message.filter(IsAdminUser())


async def _exit_to_menu(message: Message, state: FSMContext, *, header: str) -> None:
    await state.set_state()
    await message.answer(header, reply_markup=main_menu_kb(is_admin=True))
    await message.answer(build_menu_text(), reply_markup=admin_menu_kb())


@router.message(AdminDM.message, Command("cancel"))
@router.message(AdminDM.message, F.text == BT.CANCEL)
async def cancel_dm(message: Message, state: FSMContext) -> None:
    await _exit_to_menu(message, state, header="Отменено.")


@router.message(AdminDM.message)
async def send_dm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    target_tg_id = data.get("target_tg_id")
    if target_tg_id is None:
        await _exit_to_menu(
            message, state, header="Не нашёл получателя. Открой карточку заново."
        )
        return

    try:
        await message.bot.copy_message(
            chat_id=int(target_tg_id),
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        await _exit_to_menu(
            message,
            state,
            header=f"Не удалось отправить сообщение: <code>{exc}</code>",
        )
        return

    log_admin_action(
        actor_tg_id=message.from_user.id,
        action="dm",
        target_tg_id=int(target_tg_id),
    )
    await _exit_to_menu(
        message,
        state,
        header=f"✉️ Сообщение отправлено пользователю <code>{target_tg_id}</code>.",
    )
