from __future__ import annotations

import logging
from datetime import datetime, timedelta

from core.config import get_settings
from .network import UniversityClient
from .image_renderer import ScheduleRenderer
from .data_parser import TimetableParser

logger = logging.getLogger("default")


class ScheduleService:
    def __init__(self, group_name: str) -> None:
        self.settings = get_settings()
        self.renderer = ScheduleRenderer()
        self.client = UniversityClient(group_name=group_name)
        self.group_name = group_name
        logger.debug("ScheduleService инициализирован | group_name=%s", group_name)

    async def get_week_image(self, week_kind: str) -> tuple[bytes, str, str]:
        logger.info("Запрошена генерация расписания | week_kind=%s", week_kind)

        current_week_number, payload = await self._load_schedule_payload()
        logger.debug("Получены данные расписания | current_week_number=%s", current_week_number)

        week_key, week_data = self._pick_week(payload, week_kind, current_week_number)
        display_week_number = int(week_key) + 1

        logger.debug(
            "Выбрана неделя | week_key=%s | display_week_number=%s | week_kind=%s",
            week_key,
            display_week_number,
            week_kind,
        )

        highlight_day_index = self._resolve_highlight_day_index(
            current_week_number=current_week_number,
            selected_week_number=display_week_number,
        )
        logger.debug("Определён индекс подсветки дня | highlight_day_index=%s", highlight_day_index)

        normalized_payload = self._normalize_week(
            week_number=display_week_number,
            week_data=week_data,
            highlight_day_index=highlight_day_index,
        )
        logger.debug(
            "Неделя нормализована | display_week_number=%s | days_count=%s",
            display_week_number,
            len(normalized_payload.get("days", [])),
        )

        self._attach_dates_to_days(
            normalized_payload=normalized_payload,
            current_week_number=current_week_number,
            selected_display_week_number=display_week_number,
        )
        logger.debug(
            "Даты добавлены к дням недели | week_date_range=%s",
            normalized_payload.get("week_date_range", ""),
        )

        image_bytes = self._render_week(normalized_payload)
        filename = self._build_filename(display_week_number)
        week_range = normalized_payload.get("week_date_range", "")

        logger.info(
            "Расписание успешно сгенерировано | display_week_number=%s | filename=%s | bytes=%s",
            display_week_number,
            filename,
            len(image_bytes),
        )
        return image_bytes, filename, week_range

    async def _load_schedule_payload(self) -> tuple[int | None, dict]:
        logger.debug("Начало загрузки расписания через UniversityClient")
        async with self.client as client:
            result = await client.get_current_week_and_timetable()
        logger.debug("Загрузка расписания завершена")
        return result

    def _pick_week(
            self,
            payload: dict,
            week_kind: str,
            current_week_number: int | None,
    ) -> tuple[str, dict]:
        logger.debug(
            "Выбор недели через TimetableParser | week_kind=%s | current_week_number=%s",
            week_kind,
            current_week_number,
        )
        return TimetableParser.pick_week(payload, week_kind, current_week_number)

    def _resolve_highlight_day_index(
            self,
            current_week_number: int | None,
            selected_week_number: int,
    ) -> int | None:
        logger.debug(
            "Определение подсветки дня | current_week_number=%s | selected_week_number=%s",
            current_week_number,
            selected_week_number,
        )

        if current_week_number is None:
            logger.debug("Подсветка не будет выполнена: current_week_number отсутствует")
            return None

        if current_week_number != selected_week_number:
            logger.debug("Подсветка не будет выполнена: выбрана не текущая неделя")
            return None

        day_index = self._get_current_day_index()
        logger.debug("Будет подсвечен день | day_index=%s", day_index)
        return day_index

    def _normalize_week(
            self,
            week_number: int,
            week_data: dict,
            highlight_day_index: int | None,
    ) -> dict:
        logger.debug(
            "Нормализация недели | week_number=%s | highlight_day_index=%s",
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
        logger.debug("Передача данных в рендерер")
        return self.renderer.render(normalized_payload)

    def _build_filename(self, week_number: int) -> str:
        filename = f"schedule_week_{week_number}.png"
        logger.debug("Сформировано имя файла | filename=%s", filename)
        return filename

    def _get_current_day_index(self) -> int | None:
        weekday = datetime.now().weekday()
        result = weekday if 0 <= weekday <= 5 else None
        logger.debug("Текущий индекс дня вычислен | weekday=%s | result=%s", weekday, result)
        return result

    def _attach_dates_to_days(
            self,
            normalized_payload: dict,
            current_week_number: int | None,
            selected_display_week_number: int,
    ) -> None:
        logger.debug(
            "Начало генерации дат | current_week_number=%s | selected_display_week_number=%s",
            current_week_number,
            selected_display_week_number,
        )

        if current_week_number is None:
            logger.debug("Даты не будут сгенерированы: current_week_number отсутствует")
            return

        today = datetime.now().date()
        current_monday = today - timedelta(days=today.weekday())

        week_offset = selected_display_week_number - current_week_number
        selected_monday = current_monday + timedelta(days=week_offset * 7)

        logger.debug(
            "Базовые даты вычислены | today=%s | current_monday=%s | selected_monday=%s | week_offset=%s",
            today,
            current_monday,
            selected_monday,
            week_offset,
        )

        for day_payload in normalized_payload.get("days", []):
            day_index = day_payload.get("day_index")
            if day_index is None:
                logger.debug("Пропуск дня без day_index | payload=%s", day_payload)
                continue

            day_date = selected_monday + timedelta(days=day_index)
            day_payload["date"] = day_date.strftime("%d.%m")

            logger.debug(
                "Дата добавлена | day_index=%s | date=%s",
                day_index,
                day_payload["date"],
            )

        normalized_payload["week_date_range"] = self._build_week_date_range(selected_monday)
        logger.debug(
            "Диапазон недели сформирован | week_date_range=%s",
            normalized_payload["week_date_range"],
        )

    @staticmethod
    def _build_week_date_range(week_monday) -> str:
        week_saturday = week_monday + timedelta(days=5)
        return f"{week_monday.strftime('%d.%m')} - {week_saturday.strftime('%d.%m')}"
