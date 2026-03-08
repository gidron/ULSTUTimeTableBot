from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from core.config import get_settings

logger = logging.getLogger("renderer")

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
PAIR_HEADERS = ["1-я", "2-я", "3-я", "4-я", "5-я", "6-я", "7-я", "8-я"]
PAIR_TIMES = [
    "08:30-09:50",
    "10:00-11:20",
    "11:30-12:50",
    "13:30-14:50",
    "15:00-16:20",
    "16:30-17:50",
    "18:00-19:20",
    "19:30-20:50",
]

CANVAS_WIDTH = 1280
TOP_HEADER_HEIGHT = 50
PAIR_ROW_HEIGHT = 38
TIME_ROW_HEIGHT = 38
DAY_ROW_HEIGHT = 102

LEFT_COL_WIDTH = 78
PAIR_COL_WIDTHS = [183, 183, 183, 120, 120, 180, 122, 114]

GRID_LINE = (25, 25, 25)
BG = (235, 235, 235)
CURRENT_DAY_BG = (210, 225, 255)
TEXT = (20, 20, 20)


class ScheduleRenderer:
    def __init__(self) -> None:
        self.settings = get_settings()

        self.font_cell = self._load_font(11)
        self.font_regular = self._load_font(13)
        self.font_medium = self._load_font(15)
        self.font_bold = self._load_font(16, bold=True)
        self.font_left_col = self._load_font(17, bold=True)
        self.font_title = self._load_font(17)
        self.font_title_bold = self._load_font(18, bold=True)

        self.cell_padding_x = 6
        self.cell_padding_y = 5
        self.cell_spacing = 1

        logger.debug(
            "ScheduleRenderer initialized | font_path=%s",
            self.settings.font_path,
        )

    def render(self, week_payload: dict) -> bytes:
        logger.info(
            "Starting schedule rendering | group_name=%s | week_number=%s",
            week_payload.get("group_name"),
            week_payload.get("week_number"),
        )

        rows = len(week_payload["days"])
        height = TOP_HEADER_HEIGHT + PAIR_ROW_HEIGHT + TIME_ROW_HEIGHT + rows * DAY_ROW_HEIGHT

        logger.debug(
            "Canvas parameters calculated | rows=%s | width=%s | height=%s",
            rows,
            CANVAS_WIDTH,
            height,
        )

        image = Image.new("RGB", (CANVAS_WIDTH, height), BG)
        draw = ImageDraw.Draw(image)

        self._draw_top_header(draw, week_payload)
        self._draw_pair_header(draw)
        self._draw_time_header(draw)
        self._draw_body(draw, week_payload)

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        data = buffer.read()

        logger.info("Rendering completed successfully | bytes=%s", len(data))
        return data

    def _draw_top_header(self, draw: ImageDraw.ImageDraw, week_payload: dict) -> None:
        logger.debug(
            "Drawing top header | group_name=%s | week_number=%s",
            week_payload.get("group_name"),
            week_payload.get("week_number"),
        )

        y1 = 0
        y2 = TOP_HEADER_HEIGHT
        draw.rectangle([(0, y1), (CANVAS_WIDTH - 1, y2)], outline=GRID_LINE, width=1, fill=BG)

        left_label = "Расписание группы:"
        left_group = f" {week_payload['group_name']}"

        label_bbox = draw.textbbox((0, 0), left_label, font=self.font_title)
        label_w = label_bbox[2] - label_bbox[0]

        draw.text((12, 10), left_label, fill=TEXT, font=self.font_title)
        draw.text((12 + label_w, 10), left_group, fill=TEXT, font=self.font_title_bold)

        center_text = self.settings.bot_link_text
        center_bbox = draw.textbbox((0, 0), center_text, font=self.font_title)
        center_w = center_bbox[2] - center_bbox[0]
        draw.text(((CANVAS_WIDTH - center_w) / 2, 10), center_text, fill=TEXT, font=self.font_title)

        right_text = f"Неделя: {week_payload['week_number']}-я"
        right_bbox = draw.textbbox((0, 0), right_text, font=self.font_title)
        right_w = right_bbox[2] - right_bbox[0]
        draw.text((CANVAS_WIDTH - right_w - 12, 10), right_text, fill=TEXT, font=self.font_title)

    def _draw_pair_header(self, draw: ImageDraw.ImageDraw) -> None:
        logger.debug("Drawing pair header")
        y1 = TOP_HEADER_HEIGHT
        y2 = y1 + PAIR_ROW_HEIGHT
        self._draw_row_grid(draw, y1, y2, fill=BG)

        self._draw_centered_text(
            draw=draw,
            box=(0, y1, LEFT_COL_WIDTH, y2),
            text="Пары",
            font=self.font_left_col,
        )

        x = LEFT_COL_WIDTH
        for idx, name in enumerate(PAIR_HEADERS):
            width = PAIR_COL_WIDTHS[idx]
            logger.debug("Drawing pair header cell | index=%s | text=%s | width=%s", idx, name, width)
            self._draw_centered_text(
                draw=draw,
                box=(x, y1, x + width, y2),
                text=name,
                font=self.font_bold,
            )
            x += width

    def _draw_time_header(self, draw: ImageDraw.ImageDraw) -> None:
        logger.debug("Drawing time header")
        y1 = TOP_HEADER_HEIGHT + PAIR_ROW_HEIGHT
        y2 = y1 + TIME_ROW_HEIGHT
        self._draw_row_grid(draw, y1, y2, fill=BG)

        self._draw_centered_text(
            draw=draw,
            box=(0, y1, LEFT_COL_WIDTH, y2),
            text="Время",
            font=self.font_left_col,
        )

        x = LEFT_COL_WIDTH
        for idx, time_label in enumerate(PAIR_TIMES):
            width = PAIR_COL_WIDTHS[idx]
            logger.debug("Drawing time header cell | index=%s | text=%s | width=%s", idx, time_label, width)
            self._draw_centered_text(
                draw=draw,
                box=(x, y1, x + width, y2),
                text=time_label,
                font=self.font_regular,
            )
            x += width

    def _draw_body(self, draw: ImageDraw.ImageDraw, week_payload: dict) -> None:
        start_y = TOP_HEADER_HEIGHT + PAIR_ROW_HEIGHT + TIME_ROW_HEIGHT
        days = week_payload["days"]

        logger.debug("Drawing body | days_count=%s", len(days))

        for row_index, day_payload in enumerate(days):
            y1 = start_y + row_index * DAY_ROW_HEIGHT
            y2 = y1 + DAY_ROW_HEIGHT

            logger.debug(
                "Drawing day row | row_index=%s | day_index=%s | date=%s | is_current_day=%s",
                row_index,
                day_payload.get("day_index"),
                day_payload.get("date"),
                day_payload.get("is_current_day"),
            )

            fill = CURRENT_DAY_BG if day_payload.get("is_current_day") else BG
            self._draw_row_grid(draw, y1, y2, fill=fill)

            self._draw_day_label(draw, y1, y2, day_payload)
            self._draw_slots(draw, y1, y2, day_payload["slots"])

    def _draw_day_label(self, draw: ImageDraw.ImageDraw, y1: int, y2: int, day_payload: dict) -> None:
        day_index = day_payload["day_index"]
        label = WEEKDAY_NAMES[day_index] if day_index < len(WEEKDAY_NAMES) else str(day_index)
        date_text = day_payload.get("date")

        logger.debug(
            "Drawing day label | day_index=%s | label=%s | date=%s",
            day_index,
            label,
            date_text,
        )

        lines = [label]
        if date_text:
            lines.append(date_text)

        fonts = [self.font_left_col for _ in lines]

        sizes = []
        total_height = 0
        for line, font in zip(lines, fonts):
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            sizes.append((w, h))
            total_height += h

        gap = 6 if len(lines) > 1 else 0
        total_height += gap * (len(lines) - 1)

        current_y = y1 + (y2 - y1 - total_height) / 2

        for (line, font), (w, h) in zip(zip(lines, fonts), sizes):
            draw.text(
                ((LEFT_COL_WIDTH - w) / 2, current_y),
                line,
                fill=TEXT,
                font=font,
            )
            current_y += h + gap

    def _draw_slots(self, draw: ImageDraw.ImageDraw, y1: int, y2: int, slots: Iterable[str]) -> None:
        slots = list(slots)
        logger.debug("Drawing slots | slots_count=%s", len(slots))

        x = LEFT_COL_WIDTH
        for idx, slot_text in enumerate(slots):
            width = PAIR_COL_WIDTHS[idx]

            if slot_text and slot_text.strip():
                logger.debug(
                    "Drawing slot cell | slot_index=%s | width=%s | text_length=%s",
                    idx,
                    width,
                    len(slot_text.strip()),
                )
                cell_box = (x, y1, x + width, y2)
                self._draw_text_in_cell(
                    draw=draw,
                    box=cell_box,
                    text=slot_text.strip(),
                    font=self.font_cell,
                )
            else:
                logger.debug("Skipping empty slot | slot_index=%s", idx)

            x += width

    def _draw_text_in_cell(
            self,
            draw: ImageDraw.ImageDraw,
            box: tuple[int, int, int, int],
            text: str,
            font: ImageFont.FreeTypeFont,
    ) -> None:
        logger.debug("Drawing text in cell | box=%s | text_preview=%s", box, text[:80])

        x1, y1, x2, y2 = box
        inner_x1 = x1 + self.cell_padding_x
        inner_y1 = y1 + self.cell_padding_y
        inner_x2 = x2 - self.cell_padding_x
        inner_y2 = y2 - self.cell_padding_y

        max_width = inner_x2 - inner_x1
        max_height = inner_y2 - inner_y1

        wrapped_lines = self._wrap_text_lines(draw, text, max_width, font)
        fitted_lines = self._fit_lines_to_height(
            draw=draw,
            lines=wrapped_lines,
            max_height=max_height,
            font=font,
            spacing=self.cell_spacing,
            max_width=max_width,
        )

        logger.debug(
            "Text layout prepared | wrapped_lines=%s | fitted_lines=%s | max_width=%s | max_height=%s",
            len(wrapped_lines),
            len(fitted_lines),
            max_width,
            max_height,
        )

        if not fitted_lines:
            logger.debug("No fitted lines for cell, skipping draw")
            return

        text_block = "\n".join(fitted_lines)
        bbox = draw.multiline_textbbox(
            (0, 0),
            text_block,
            font=font,
            spacing=self.cell_spacing,
            align="center",
        )
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        text_x = inner_x1 + max((max_width - text_w) / 2, 0)
        text_y = inner_y1 + max((max_height - text_h) / 2, 0)

        draw.multiline_text(
            (text_x, text_y),
            text_block,
            fill=TEXT,
            font=font,
            spacing=self.cell_spacing,
            align="center",
        )

    def _draw_centered_text(
            self,
            draw: ImageDraw.ImageDraw,
            box: tuple[int, int, int, int],
            text: str,
            font: ImageFont.FreeTypeFont,
    ) -> None:
        logger.debug("Drawing centered text | box=%s | text=%s", box, text)

        x1, y1, x2, y2 = box
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(
            (x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2 - 1),
            text,
            fill=TEXT,
            font=font,
        )

    def _draw_row_grid(self, draw: ImageDraw.ImageDraw, y1: int, y2: int, *, fill: tuple[int, int, int]) -> None:
        logger.debug("Drawing row grid | y1=%s | y2=%s | fill=%s", y1, y2, fill)

        draw.rectangle([(0, y1), (CANVAS_WIDTH - 1, y2)], outline=GRID_LINE, width=1, fill=fill)
        draw.line([(LEFT_COL_WIDTH, y1), (LEFT_COL_WIDTH, y2)], fill=GRID_LINE, width=1)

        x = LEFT_COL_WIDTH
        for width in PAIR_COL_WIDTHS[:-1]:
            x += width
            draw.line([(x, y1), (x, y2)], fill=GRID_LINE, width=1)

    def _wrap_text_lines(
            self,
            draw: ImageDraw.ImageDraw,
            text: str,
            max_width: int,
            font: ImageFont.FreeTypeFont,
    ) -> list[str]:
        logger.debug(
            "Wrapping text lines | text_length=%s | max_width=%s",
            len(text),
            max_width,
        )

        final_lines: list[str] = []

        for raw_line in text.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                final_lines.append("")
                continue

            words = raw_line.split()
            current = words[0]

            for word in words[1:]:
                trial = f"{current} {word}"
                if self._text_width(draw, trial, font) <= max_width:
                    current = trial
                else:
                    final_lines.append(current)
                    current = word

            final_lines.append(current)

        logger.debug("Text wrapped | lines_count=%s", len(final_lines))
        return final_lines

    def _fit_lines_to_height(
            self,
            draw: ImageDraw.ImageDraw,
            lines: list[str],
            max_height: int,
            font: ImageFont.FreeTypeFont,
            spacing: int,
            max_width: int,
    ) -> list[str]:
        logger.debug(
            "Fitting lines to height | lines_count=%s | max_height=%s | max_width=%s",
            len(lines),
            max_height,
            max_width,
        )

        if not lines:
            return []

        fitted: list[str] = []

        for line in lines:
            candidate = fitted + [line]
            if self._lines_height(draw, candidate, font, spacing) <= max_height:
                fitted.append(line)
            else:
                break

        if not fitted:
            logger.debug("No lines fit into available height")
            return []

        if len(fitted) < len(lines):
            logger.debug("Lines truncated to fit height")
            fitted[-1] = self._truncate_line_with_ellipsis(
                draw=draw,
                line=fitted[-1],
                font=font,
                max_width=max_width,
            )

        return fitted

    def _truncate_line_with_ellipsis(
            self,
            draw: ImageDraw.ImageDraw,
            line: str,
            font: ImageFont.FreeTypeFont,
            max_width: int,
    ) -> str:
        logger.debug("Truncating line with ellipsis | line=%s | max_width=%s", line, max_width)

        ellipsis = "..."
        if self._text_width(draw, line, font) <= max_width:
            return line

        cut = line
        while cut and self._text_width(draw, cut + ellipsis, font) > max_width:
            cut = cut[:-1].rstrip()

        result = (cut + ellipsis) if cut else ellipsis
        logger.debug("Truncated line result=%s", result)
        return result

    def _lines_height(
            self,
            draw: ImageDraw.ImageDraw,
            lines: list[str],
            font: ImageFont.FreeTypeFont,
            spacing: int,
    ) -> int:
        text = "\n".join(lines)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing)
        height = bbox[3] - bbox[1]
        logger.debug("Calculated lines height | lines_count=%s | height=%s", len(lines), height)
        return height

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        return width

    def _load_font(self, size: int, bold: bool = False):
        candidates = []

        if self.settings.font_path:
            candidates.append(self.settings.font_path)

        if bold:
            candidates.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "C:/Windows/Fonts/arialbd.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ])
        else:
            candidates.extend([
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/arial.ttf",
                "/Library/Fonts/Arial.ttf",
            ])

        for path in candidates:
            if path and Path(path).exists():
                try:
                    font = ImageFont.truetype(path, size=size)
                    logger.debug("Font loaded successfully | path=%s | size=%s | bold=%s", path, size, bold)
                    return font
                except OSError:
                    logger.debug("Failed to load font candidate | path=%s | size=%s | bold=%s", path, size, bold)
                    continue

        logger.warning("No custom/system font loaded, fallback to default font | size=%s | bold=%s", size, bold)
        return ImageFont.load_default()
