"""Кеш сессии «расписание на день»: TTL 15 мин, предпросчёт двух ISO-неделей."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from cachetools import TTLCache

from services.schedule.day_for_date import (
    DayScheduleSnapshot,
    build_day_schedule_snapshot,
    dates_two_iso_weeks_intersect_semester,
)
from services.schedule.parser import TimetableParseError

DAY_SCHEDULE_SESSION_TTL_SEC = 15 * 60
_MAX_ENTRIES = 50_000

_cache: TTLCache[tuple[int, str], DayScheduleSession] = TTLCache(
    maxsize=_MAX_ENTRIES, ttl=DAY_SCHEDULE_SESSION_TTL_SEC
)


@dataclass
class DayScheduleSession:
    api_current_week: int
    payload: dict[str, Any]
    frozen_today: date
    group_name: str
    precomputed: dict[date, DayScheduleSnapshot | Literal["sunday"]]


def _cache_key(tg_id: int, group_name: str) -> tuple[int, str]:
    return (tg_id, group_name.strip())


def get_day_schedule_session(tg_id: int, group_name: str) -> DayScheduleSession | None:
    return _cache.get(_cache_key(tg_id, group_name))


def invalidate_day_schedule_session(tg_id: int, group_name: str) -> None:
    _cache.pop(_cache_key(tg_id, group_name), None)


def build_precomputed_for_anchor(
    anchor: date,
    *,
    api_current_week: int,
    payload: dict[str, Any],
    group_name: str,
    frozen_today: date,
) -> dict[date, DayScheduleSnapshot | Literal["sunday"]]:
    precomputed: dict[date, DayScheduleSnapshot | Literal["sunday"]] = {}
    for d in dates_two_iso_weeks_intersect_semester(anchor, frozen_today):
        try:
            out = build_day_schedule_snapshot(
                d,
                api_current_week=api_current_week,
                payload=payload,
                group_name=group_name,
                today=frozen_today,
            )
        except TimetableParseError:
            continue
        precomputed[d] = out
    return precomputed


def save_day_schedule_session(
    tg_id: int,
    group_name: str,
    *,
    api_current_week: int,
    payload: dict[str, Any],
    frozen_today: date,
    anchor_date: date,
) -> DayScheduleSession:
    precomputed = build_precomputed_for_anchor(
        anchor_date,
        api_current_week=api_current_week,
        payload=payload,
        group_name=group_name,
        frozen_today=frozen_today,
    )
    session = DayScheduleSession(
        api_current_week=api_current_week,
        payload=payload,
        frozen_today=frozen_today,
        group_name=group_name,
        precomputed=precomputed,
    )
    _cache[_cache_key(tg_id, group_name)] = session
    return session
