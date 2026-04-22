"""Аккаунты владельца/оператора бота, недоступные для бана и удаления делегированными админами."""

from __future__ import annotations

from core.config import get_settings


def protected_operator_tg_ids() -> frozenset[int]:
    """Telegram ID, которые нельзя забанить или удалить через админку (кроме действий самого этого пользователя)."""
    return frozenset({int(get_settings().developer_chat_id)})


def is_protected_operator(tg_id: int | str) -> bool:
    return int(tg_id) in protected_operator_tg_ids()


def can_admin_ban_or_delete_target(*, actor_tg_id: int | str, target_tg_id: int | str) -> bool:
    """Делегированный админ не может банить/удалять защищённого оператора (см. developer_chat_id)."""
    if int(actor_tg_id) == int(target_tg_id):
        return True
    return not is_protected_operator(target_tg_id)
