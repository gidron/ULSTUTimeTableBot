from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from constants.buttons_text import ButtonText as BT
from database.models import User
from handlers.admin.tools.texts import build_menu_text, build_user_card_text
from keyboards.admin import admin_menu_kb
from keyboards.reply import main_menu_kb
from misc.admin_audit import log_admin_action
from misc.filters import IsAdminUser
from misc.states import AdminAddUser

router = Router(name="admin_state_add_user")
router.message.filter(IsAdminUser())


def _parse_tg_id(raw: str) -> int:
    s = raw.strip()
    if not s or not s.isdigit():
        raise ValueError
    return int(s)


async def _exit_to_menu(message: Message, state: FSMContext, *, header: str) -> None:
    await state.set_state()
    await message.answer(header, reply_markup=main_menu_kb(is_admin=True))
    await message.answer(build_menu_text(), reply_markup=admin_menu_kb())


@router.message(AdminAddUser.identifier, Command("cancel"))
@router.message(AdminAddUser.identifier, F.text == BT.CANCEL)
async def cancel_add_user(message: Message, state: FSMContext) -> None:
    await _exit_to_menu(message, state, header="Добавление отменено.")


@router.message(AdminAddUser.identifier)
async def handle_add_user(message: Message, state: FSMContext) -> None:
    raw = message.text or ""
    try:
        tid = _parse_tg_id(raw)
    except ValueError:
        await message.answer(
            "Нужен <b>числовой Telegram ID</b> (только цифры, без пробелов)."
        )
        return

    tg_id_str = str(tid)
    user = await User.get_or_none(tg_id=tg_id_str)
    if user is None:
        user = await User.create(
            tg_id=tg_id_str,
            name="Пользователь",
            username=None,
            is_active=True,
            group_name=None,
        )
    else:
        user.is_active = True
        await user.save()

    log_admin_action(
        actor_tg_id=message.from_user.id,
        action="add_user",
        target_tg_id=tid,
    )

    await _exit_to_menu(
        message,
        state,
        header=build_user_card_text(
            user,
            header=(
                "<b>Пользователь добавлен</b>\n"
                "При первом <code>/start</code> одобрение не требуется — сразу "
                "запрос группы. До <code>/start</code> бот не может написать в ЛС."
            ),
        ),
    )
