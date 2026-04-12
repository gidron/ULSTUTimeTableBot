"""Оркестрация: загрузка расписания, нормализация, даты, генерация PNG."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from constants.schedule_layout import ScheduleLayout
from core.config import get_settings
from core.redis import get_redis
from services.network import UniversityClient

from services.schedule.parser import TimetableParser
from services.schedule.ports import ScheduleImageRenderer, TimetableSource
from services.schedule.redis_cache import (
    get_cached_schedule_image,
    set_cached_schedule_image,
)
from services.schedule.renderer import ScheduleRenderer
from services.schedule.week_dates import (
    attach_dates_to_week_days,
    compute_highlight_day_index,
)

logger = logging.getLogger("default")

_schedule_gen_limit_sem: asyncio.Semaphore | None = None


def _get_schedule_gen_limit_sem() -> asyncio.Semaphore | None:
    """Общий лимит параллельных генераций; None если лимит отключён (≤0)."""
    global _schedule_gen_limit_sem
    limit = get_settings().schedule_generation_concurrency
    if limit <= 0:
        return None
    if _schedule_gen_limit_sem is None:
        _schedule_gen_limit_sem = asyncio.Semaphore(limit)
    return _schedule_gen_limit_sem


@asynccontextmanager
async def _schedule_generation_slot() -> AsyncIterator[None]:
    sem = _get_schedule_gen_limit_sem()
    if sem is None:
        yield
        return
    async with sem:
        yield


class ScheduleService:
    """Сборка расписания группы в картинку на неделю (текущая / следующая)."""

    def __init__(
        self,
        group_name: str,
        *,
        timetable_source: TimetableSource | None = None,
        image_renderer: ScheduleImageRenderer | None = None,
        clock: Callable[[], datetime] | None = None,
        schedule_title_prefix: str = "Расписание группы:",
        include_study_group_in_slots: bool = False,
    ) -> None:
        """По умолчанию — UniversityClient, ScheduleRenderer и datetime.now."""
        self.group_name = group_name
        self._schedule_title_prefix = schedule_title_prefix
        self._include_study_group_in_slots = include_study_group_in_slots
        self._timetable_source = timetable_source or UniversityClient(
            group_name=group_name
        )
        self._image_renderer = image_renderer or ScheduleRenderer()
        self._clock = clock or datetime.now
        logger.debug("ScheduleService initialized | group_name=%s", group_name)

    def _schedule_reference(self) -> datetime:
        """Момент «сейчас» для подсветки дня и дат; при schedule_timezone — в этой зоне."""
        tz = get_settings().schedule_timezone
        if tz:
            return datetime.now(ZoneInfo(tz))
        return self._clock()

    def _schedule_cache_scope(self) -> str:
        """Разделение кэша группы и расписания преподавателя (разная вёрстка)."""
        return "teacher" if self._include_study_group_in_slots else "group"

    async def get_week_image(
        self,
        week_kind: str,
        *,
        layout: ScheduleLayout = ScheduleLayout.HORIZONTAL,
    ) -> tuple[bytes, str, str]:
        """Возвращает PNG, имя файла и строку диапазона дат. week_kind: 'current' | 'next'."""
        logger.info(
            "Generating schedule image | week_kind=%s | layout=%s",
            week_kind,
            layout.value,
        )

        layout_key = layout.value
        settings = get_settings()
        if settings.schedule_cache_enabled and get_redis() is not None:
            local_date = self._schedule_reference().date()
            scope = self._schedule_cache_scope()
            cached = await get_cached_schedule_image(
                self.group_name, week_kind, local_date, scope, layout_key
            )
            if cached is not None:
                logger.info("Schedule image cache hit | week_kind=%s", week_kind)
                return cached

        async with _schedule_generation_slot():
            result = await self._get_week_image_impl(week_kind, layout=layout)

        if settings.schedule_cache_enabled and get_redis() is not None:
            local_date = self._schedule_reference().date()
            scope = self._schedule_cache_scope()
            image_bytes, filename, week_range = result
            await set_cached_schedule_image(
                self.group_name,
                week_kind,
                local_date,
                scope,
                layout_key,
                image_bytes,
                filename,
                week_range,
            )

        return result

    async def _get_week_image_impl(
        self, week_kind: str, *, layout: ScheduleLayout
    ) -> tuple[bytes, str, str]:
        current_week_number, payload = await self._load_schedule_payload()
        logger.debug(
            "Schedule payload loaded | current_week_number=%s", current_week_number
        )

        week_key, week_data = self._pick_week(payload, week_kind, current_week_number)
        display_week_number = int(week_key) + 1

        logger.debug(
            "Week selected | week_key=%s | display_week_number=%s | week_kind=%s",
            week_key,
            display_week_number,
            week_kind,
        )

        ref = self._schedule_reference()
        highlight_day_index = compute_highlight_day_index(
            current_week_number,
            display_week_number,
            reference=ref,
        )
        logger.debug(
            "Resolved highlight day index | highlight_day_index=%s", highlight_day_index
        )

        normalized_payload = self._normalize_week(
            week_number=display_week_number,
            week_data=week_data,
            highlight_day_index=highlight_day_index,
        )
        logger.debug(
            "Week normalized | display_week_number=%s | days_count=%s",
            display_week_number,
            len(normalized_payload.get("days", [])),
        )

        logger.debug(
            "Generating day dates | current_week_number=%s | selected_display_week_number=%s",
            current_week_number,
            display_week_number,
        )
        if current_week_number is None:
            logger.debug("Skipping date generation: current_week_number is missing")
        else:
            attach_dates_to_week_days(
                normalized_payload,
                current_week_number,
                display_week_number,
                today=ref.date(),
            )
        logger.debug(
            "Dates attached to week days | week_date_range=%s",
            normalized_payload.get("week_date_range", ""),
        )

        image_bytes = await asyncio.to_thread(
            self._render_week, normalized_payload, layout
        )
        filename = self._build_filename(display_week_number, layout=layout)
        week_range = normalized_payload.get("week_date_range", "")

        logger.info(
            "Schedule image generated | display_week_number=%s | filename=%s | bytes=%s",
            display_week_number,
            filename,
            len(image_bytes),
        )
        return image_bytes, filename, week_range

    async def _load_schedule_payload(self) -> tuple[int | None, dict]:
        logger.debug("Loading schedule via timetable source")
        async with self._timetable_source as client:
            result = await client.get_current_week_and_timetable()
        logger.debug("Schedule load finished")
        return result

    def _pick_week(
        self,
        payload: dict,
        week_kind: str,
        current_week_number: int | None,
    ) -> tuple[str, dict]:
        logger.debug(
            "Picking week via TimetableParser | week_kind=%s | current_week_number=%s",
            week_kind,
            current_week_number,
        )
        return TimetableParser.pick_week(payload, week_kind, current_week_number)

    def _normalize_week(
        self,
        week_number: int,
        week_data: dict,
        highlight_day_index: int | None,
    ) -> dict:
        logger.debug(
            "Normalizing week | week_number=%s | highlight_day_index=%s",
            week_number,
            highlight_day_index,
        )
        return TimetableParser.normalize_week(
            week_number=str(week_number),
            week_data=week_data,
            group_name=self.group_name,
            highlight_day_index=highlight_day_index,
            schedule_title_prefix=self._schedule_title_prefix,
            include_study_group_in_slots=self._include_study_group_in_slots,
        )

    def _render_week(
        self, normalized_payload: dict, layout: ScheduleLayout
    ) -> bytes:
        logger.debug("Sending payload to renderer | layout=%s", layout.value)
        return self._image_renderer.render(normalized_payload, layout=layout)

    def _build_filename(self, week_number: int, *, layout: ScheduleLayout) -> str:
        suffix = "_vertical" if layout == ScheduleLayout.VERTICAL else ""
        filename = f"schedule_week_{week_number}{suffix}.png"
        logger.debug("Built output filename | filename=%s", filename)
        return filename
