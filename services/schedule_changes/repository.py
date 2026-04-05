"""Асинхронный доступ к моделям Tortoise для слепков и рассылки уведомлений."""

from __future__ import annotations

from tortoise.expressions import Q

from database.models import ScheduleChangeDigest, ScheduleSnapshot, User


async def get_schedule_snapshot(group_name: str) -> ScheduleSnapshot | None:
    """Последний сохранённый слепок группы или None."""
    return await ScheduleSnapshot.get_or_none(group_name=group_name)


async def create_schedule_snapshot_baseline(
    group_name: str,
    week_number: int,
    payload_hash: str,
    payload: list,
) -> None:
    """Первая запись слепка без уведомления пользователей."""
    await ScheduleSnapshot.create(
        group_name=group_name,
        week_number=week_number,
        payload_hash=payload_hash,
        payload=payload,
    )


async def save_schedule_snapshot_update(
    snapshot: ScheduleSnapshot,
    week_number: int,
    payload_hash: str,
    payload: list,
) -> None:
    """Обновляет слепок после проверки (номер недели API, хеш, тело)."""
    snapshot.week_number = week_number
    snapshot.payload_hash = payload_hash
    snapshot.payload = payload
    await snapshot.save()


async def schedule_change_digest_exists(digest: str) -> bool:
    """Уже отправляли уведомление с таким набором изменений."""
    return await ScheduleChangeDigest.get_or_none(digest=digest) is not None


async def create_schedule_change_digest(group_name: str, digest: str) -> None:
    """Фиксирует digest, чтобы не дублировать одинаковые уведомления."""
    await ScheduleChangeDigest.create(group_name=group_name, digest=digest)


async def list_group_names_for_change_notify() -> list[str]:
    """Уникальные группы активных пользователей с включёнными уведомлениями об изменениях."""
    rows = (
        await User.filter(
            Q(is_active=True)
            & Q(group_name__not_isnull=True)
            & Q(notify_by_change=True)
        )
        .distinct()
        .values_list("group_name", flat=True)
    )
    return [group for group in rows if group]


async def list_recipient_tg_ids(group_name: str) -> list:
    """Список tg_id для рассылки по одной группе."""
    return await User.filter(
        Q(is_active=True) & Q(group_name=group_name) & Q(notify_by_change=True)
    ).values_list("tg_id", flat=True)
