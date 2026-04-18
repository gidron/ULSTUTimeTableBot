"""Callback-хэндлеры админ-панели: навигация, список, карточка, действия."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database.models import User
from handlers.admin.tools.queries import filtered_users_queryset
from handlers.admin.tools.texts import (
    BROADCAST_HINT,
    SEARCH_PROMPT,
    build_delete_confirm_text,
    build_dm_prompt_text,
    build_list_text,
    build_menu_text,
    build_stats_text,
    build_user_card_text,
)
from keyboards.admin import (
    PAGE_SIZE,
    admin_menu_kb,
    broadcast_hint_kb,
    delete_confirm_kb,
    dm_cancel_kb,
    post_delete_nav_kb,
    search_prompt_kb,
    stats_kb,
    user_card_kb,
    users_list_kb,
)
from keyboards.factories import (
    AdminActionCallback,
    AdminListCallback,
    AdminMenuCallback,
    AdminUserCallback,
)
from keyboards.reply import cancel_kb
from misc.admin_audit import log_admin_action
from misc.filters import IsAdminUser
from misc.states import AdminDM, AdminSearch

router = Router(name="admin_callbacks")
router.callback_query.filter(IsAdminUser())


# ---------- main menu ----------


@router.callback_query(AdminMenuCallback.filter(F.page == "root"))
async def menu_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state()
    await callback.answer()
    await callback.message.edit_text(build_menu_text(), reply_markup=admin_menu_kb())


@router.callback_query(AdminMenuCallback.filter(F.page == "stats"))
async def menu_stats(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state()
    await callback.answer()
    await callback.message.edit_text(await build_stats_text(), reply_markup=stats_kb())


@router.callback_query(AdminMenuCallback.filter(F.page == "search"))
async def menu_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(AdminSearch.query)
    await callback.message.edit_text(SEARCH_PROMPT, reply_markup=search_prompt_kb())
    await callback.message.answer("Жду поисковый запрос…", reply_markup=cancel_kb)


@router.callback_query(AdminMenuCallback.filter(F.page == "bcast"))
async def menu_broadcast_hint(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state()
    await callback.answer()
    await callback.message.edit_text(BROADCAST_HINT, reply_markup=broadcast_hint_kb())


# ---------- users list ----------


@router.callback_query(AdminListCallback.filter())
async def show_users_list(
    callback: CallbackQuery,
    callback_data: AdminListCallback,
    state: FSMContext,
) -> None:
    await state.set_state()
    flt = callback_data.flt
    qs = filtered_users_queryset(flt)
    total = await qs.count()
    total_pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = max(0, min(callback_data.page, total_pages - 1))

    users = (
        await qs.order_by("group_name", "name")
        .offset(page * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )

    await callback.answer()
    await callback.message.edit_text(
        build_list_text(flt, total, page, total_pages),
        reply_markup=users_list_kb(
            users,
            filter_key=flt,
            page=page,
            total_pages=total_pages,
        ),
    )


# ---------- user card ----------


async def _render_card(
    callback: CallbackQuery,
    user: User,
    *,
    back_flt: str,
    back_page: int,
) -> None:
    await callback.message.edit_text(
        build_user_card_text(user),
        reply_markup=user_card_kb(
            user,
            actor_tg_id=callback.from_user.id,
            back_flt=back_flt,
            back_page=back_page,
        ),
    )


async def _load_target(callback: CallbackQuery, tg_id: int) -> User | None:
    user = await User.get_or_none(tg_id=str(tg_id))
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
    return user


@router.callback_query(AdminUserCallback.filter())
async def open_user_card(
    callback: CallbackQuery,
    callback_data: AdminUserCallback,
    state: FSMContext,
) -> None:
    await state.set_state()
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    await callback.answer()
    await _render_card(
        callback,
        user,
        back_flt=callback_data.back_flt,
        back_page=callback_data.back_page,
    )


# ---------- per-action handlers ----------


def _is_self(callback: CallbackQuery, user: User) -> bool:
    return int(user.tg_id) == int(callback.from_user.id)


@router.callback_query(AdminActionCallback.filter(F.action == "ban"))
async def action_ban(
    callback: CallbackQuery, callback_data: AdminActionCallback
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    if _is_self(callback, user):
        await callback.answer("Нельзя забанить самого себя", show_alert=True)
        return

    user.is_active = not user.is_active
    await user.save()
    log_admin_action(
        actor_tg_id=callback.from_user.id,
        action="unban" if user.is_active else "ban",
        target_tg_id=int(user.tg_id),
    )
    await callback.answer("Разбанен" if user.is_active else "Забанен")
    await _render_card(
        callback,
        user,
        back_flt=callback_data.back_flt,
        back_page=callback_data.back_page,
    )


@router.callback_query(AdminActionCallback.filter(F.action == "admin"))
async def action_admin(
    callback: CallbackQuery, callback_data: AdminActionCallback
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    if _is_self(callback, user) and user.is_admin:
        await callback.answer(
            "Нельзя снять админ-права с самого себя", show_alert=True
        )
        return

    user.is_admin = not user.is_admin
    await user.save()
    log_admin_action(
        actor_tg_id=callback.from_user.id,
        action="grant_admin" if user.is_admin else "revoke_admin",
        target_tg_id=int(user.tg_id),
    )
    await callback.answer("Назначен админом" if user.is_admin else "Снят с админов")
    await _render_card(
        callback,
        user,
        back_flt=callback_data.back_flt,
        back_page=callback_data.back_page,
    )


@router.callback_query(AdminActionCallback.filter(F.action == "delete"))
async def action_delete_prompt(
    callback: CallbackQuery, callback_data: AdminActionCallback
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    if _is_self(callback, user):
        await callback.answer("Нельзя удалить самого себя", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        build_delete_confirm_text(user),
        reply_markup=delete_confirm_kb(
            user,
            back_flt=callback_data.back_flt,
            back_page=callback_data.back_page,
        ),
    )


@router.callback_query(AdminActionCallback.filter(F.action == "delete_confirm"))
async def action_delete_confirm(
    callback: CallbackQuery, callback_data: AdminActionCallback
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    if _is_self(callback, user):
        await callback.answer("Нельзя удалить самого себя", show_alert=True)
        return

    target_id = int(user.tg_id)
    await user.delete()
    log_admin_action(
        actor_tg_id=callback.from_user.id,
        action="delete_user",
        target_tg_id=target_id,
    )
    await callback.answer("Удалено")
    await callback.message.edit_text(
        f"🗑 Пользователь <code>{target_id}</code> удалён.",
        reply_markup=post_delete_nav_kb(
            back_flt=callback_data.back_flt,
            back_page=callback_data.back_page,
        ),
    )


@router.callback_query(AdminActionCallback.filter(F.action == "delete_cancel"))
async def action_delete_cancel(
    callback: CallbackQuery, callback_data: AdminActionCallback
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    await callback.answer("Отменено")
    await _render_card(
        callback,
        user,
        back_flt=callback_data.back_flt,
        back_page=callback_data.back_page,
    )


@router.callback_query(AdminActionCallback.filter(F.action == "dm"))
async def action_dm_prompt(
    callback: CallbackQuery,
    callback_data: AdminActionCallback,
    state: FSMContext,
) -> None:
    user = await _load_target(callback, callback_data.tg_id)
    if user is None:
        return
    await state.set_state(AdminDM.message)
    await state.update_data(
        target_tg_id=int(user.tg_id),
        back_flt=callback_data.back_flt,
        back_page=callback_data.back_page,
    )
    await callback.answer()
    await callback.message.edit_text(
        build_dm_prompt_text(user),
        reply_markup=dm_cancel_kb(),
    )
