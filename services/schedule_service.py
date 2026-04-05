"""Оркестрация: загрузка расписания, нормализация, даты, генерация PNG."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from services.data_parser import TimetableParser
from services.image_renderer import ScheduleRenderer
from services.network import UniversityClient
from services.ports import ScheduleImageRenderer, TimetableSource
from services.schedule_week_dates import (
    attach_dates_to_week_days,
    compute_highlight_day_index,
)

logger = logging.getLogger("default")


class ScheduleService:
    """Сборка расписания группы в картинку на неделю (текущая / следующая)."""

    def __init__(
        self,
        group_name: str,
        *,
        timetable_source: TimetableSource | None = None,
        image_renderer: ScheduleImageRenderer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """По умолчанию — UniversityClient, ScheduleRenderer и datetime.now."""
        self.group_name = group_name
        self._timetable_source = timetable_source or UniversityClient(
            group_name=group_name
        )
        self._image_renderer = image_renderer or ScheduleRenderer()
        self._clock = clock or datetime.now
        logger.debug("ScheduleService initialized | group_name=%s", group_name)

    async def get_week_image(self, week_kind: str) -> tuple[bytes, str, str]:
        """Возвращает PNG, имя файла и строку диапазона дат. week_kind: 'current' | 'next'."""
        logger.info("Generating schedule image | week_kind=%s", week_kind)

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

        highlight_day_index = compute_highlight_day_index(
            current_week_number,
            display_week_number,
            reference=self._clock(),
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
                today=self._clock().date(),
            )
        logger.debug(
            "Dates attached to week days | week_date_range=%s",
            normalized_payload.get("week_date_range", ""),
        )

        image_bytes = self._render_week(normalized_payload)
        filename = self._build_filename(display_week_number)
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
        )

    def _render_week(self, normalized_payload: dict) -> bytes:
        logger.debug("Sending payload to renderer")
        return self._image_renderer.render(normalized_payload)

    def _build_filename(self, week_number: int) -> str:
        filename = f"schedule_week_{week_number}.png"
        logger.debug("Built output filename | filename=%s", filename)
        return filename
