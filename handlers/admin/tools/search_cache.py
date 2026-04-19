"""Маленький in-memory LRU-кэш последних поисковых запросов админа."""

from __future__ import annotations

from collections import OrderedDict

_MAX_ENTRIES = 256
_LAST_QUERY: "OrderedDict[int, str]" = OrderedDict()


def remember(actor_tg_id: int, query: str) -> None:
    """Сохраняет последний поисковый запрос пользователя-админа."""
    _LAST_QUERY[actor_tg_id] = query
    _LAST_QUERY.move_to_end(actor_tg_id)
    while len(_LAST_QUERY) > _MAX_ENTRIES:
        _LAST_QUERY.popitem(last=False)


def get(actor_tg_id: int) -> str | None:
    query = _LAST_QUERY.get(actor_tg_id)
    if query is not None:
        _LAST_QUERY.move_to_end(actor_tg_id)
    return query


def clear(actor_tg_id: int) -> None:
    _LAST_QUERY.pop(actor_tg_id, None)
