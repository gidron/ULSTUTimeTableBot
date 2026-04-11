"""Фоновая проверка расписания по расписанию часов и рассылка изменений в Telegram."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot

from services.network import UniversityClient
from services.schedule_changes import (
    change_detector,
    hashing,
    message_renderer,
    repository,
)
from services.schedule.redis_cache import invalidate_group_schedule_cache
from services.schedule_changes import snapshot_builder

logger = logging.getLogger("default")


class ScheduleChangeNotifier:
    """Цикл ожидания, загрузка API, сравнение с БД, отправка сообщений подписчикам группы."""

    RUN_HOURS = (8, 13, 18, 21)

    def __init__(
        self,
        *,
        university_client_class: type[UniversityClient] = UniversityClient,
    ) -> None:
        """university_client_class — для тестов (подмена клиента УлГТУ)."""
        self._university_client_class = university_client_class

    async def run_forever(self, bot: Bot) -> None:
        """Бесконечный цикл: сон до ближайшего слота RUN_HOURS, затем check_and_notify."""
        while True:
            sleep_seconds = self._seconds_until_next_run()
            logger.info(
                "Sleeping until next schedule check | sleep_seconds=%s", sleep_seconds
            )
            await asyncio.sleep(sleep_seconds)
            await self.check_and_notify(bot)

    async def check_and_notify(self, bot: Bot) -> None:
        """Один проход по всем группам с подпиской на изменения."""
        groups = await repository.list_group_names_for_change_notify()
        logger.info("Starting schedule change check | groups_count=%s", len(groups))

        for group_name in groups:
            try:
                await self._process_group(bot, group_name)
            except Exception:
                logger.exception("Error while processing group | group=%s", group_name)

    async def _process_group(self, bot: Bot, group_name: str) -> None:
        now = datetime.now()
        async with self._university_client_class(group_name=group_name) as client:
            current_week, payload = await client.get_current_week_and_timetable()

        two_week_slots = snapshot_builder.build_two_week_slots(
            payload=payload, api_current_week=current_week
        )
        if not two_week_slots:
            logger.warning("Failed to build schedule snapshot | group=%s", group_name)
            return

        payload_hash = hashing.hash_payload(two_week_slots)

        snapshot = await repository.get_schedule_snapshot(group_name)
        if snapshot is None:
            await repository.create_schedule_snapshot_baseline(
                group_name=group_name,
                week_number=current_week,
                payload_hash=payload_hash,
                payload=two_week_slots,
            )
            logger.info(
                "Created baseline snapshot without notification | group=%s", group_name
            )
            return

        old_slots = snapshot.payload if isinstance(snapshot.payload, list) else []
        changes = change_detector.build_changes(
            old_slots=old_slots,
            new_slots=two_week_slots,
            now=now,
            api_current_week=current_week,
        )

        await repository.save_schedule_snapshot_update(
            snapshot,
            current_week,
            payload_hash,
            two_week_slots,
        )

        if not changes:
            logger.info("No schedule changes | group=%s", group_name)
            return

        await invalidate_group_schedule_cache(group_name)

        digest = hashing.hash_payload(changes)
        if await repository.schedule_change_digest_exists(digest):
            logger.info(
                "Duplicate change digest, notification skipped | group=%s", group_name
            )
            return

        await repository.create_schedule_change_digest(group_name, digest=digest)
        await self._notify_group_users(
            bot=bot,
            group_name=group_name,
            changes=changes,
            api_current_week=current_week,
        )

    async def _notify_group_users(
        self,
        bot: Bot,
        group_name: str,
        changes: list[dict],
        *,
        api_current_week: int,
    ) -> None:
        users = await repository.list_recipient_tg_ids(group_name)
        if not users:
            return

        text = message_renderer.render_schedule_change_message(
            group_name=group_name,
            changes=changes,
            api_current_week=api_current_week,
        )
        for tg_id in users:
            try:
                await bot.send_message(chat_id=int(tg_id), text=text)
            except Exception:
                logger.exception(
                    "Failed to send schedule change notification | tg_id=%s", tg_id
                )

    def _seconds_until_next_run(self) -> int:
        """Секунды до ближайшего часа из RUN_HOURS (сегодня или завтра)."""
        now = datetime.now()
        candidates = []
        for hour in self.RUN_HOURS:
            candidates.append(now.replace(hour=hour, minute=0, second=0, microsecond=0))

        future_candidates = [item for item in candidates if item > now]
        if future_candidates:
            target = min(future_candidates)
        else:
            target = candidates[0] + timedelta(days=1)

        return max(1, int((target - now).total_seconds()))
