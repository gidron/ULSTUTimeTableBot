"""Хелперы поверх Tortoise для админ-панели."""

from __future__ import annotations

from tortoise.queryset import QuerySet

from database.models import User


def filtered_users_queryset(filter_key: str) -> QuerySet[User]:
    qs = User.all()
    if filter_key == "active":
        qs = qs.filter(is_active=True)
    elif filter_key == "banned":
        qs = qs.filter(is_active=False)
    elif filter_key == "admins":
        qs = qs.filter(is_admin=True)
    elif filter_key == "nogroup":
        qs = qs.filter(group_name__isnull=True)
    return qs
