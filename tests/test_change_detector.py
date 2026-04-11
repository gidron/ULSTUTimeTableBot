"""Тесты сравнения слотов и фильтра уведомлений."""

from __future__ import annotations

from datetime import datetime

from services.schedule_changes.change_detector import (
    build_changes,
    compare_slot,
    normalize_slot_list,
    should_notify_slot,
)
from services.schedule_changes.models import LessonEntry


def test_normalize_slot_list_fills_week_number() -> None:
    rows = [
        {"week_number": "5", "day_index": 0, "slot_index": 0, "lessons": []},
        {"day_index": 1, "slot_index": 0, "lessons": []},
    ]
    out = normalize_slot_list(rows, api_current_week=10)
    assert out[0]["week_number"] == 5
    assert out[1]["week_number"] == 10


def test_compare_slot_cancelled() -> None:
    old = [LessonEntry("Матан", "Иванов", "101")]
    new: list[LessonEntry] = []
    changes = compare_slot(10, 0, 0, old, new)
    assert len(changes) == 1
    assert changes[0]["type"] == "cancelled"


def test_compare_slot_added() -> None:
    old: list[LessonEntry] = []
    new = [LessonEntry("Физика", "Петров", "202")]
    changes = compare_slot(10, 1, 2, old, new)
    assert len(changes) == 1
    assert changes[0]["type"] == "added"


def test_compare_slot_room_changed() -> None:
    old = [LessonEntry("Линал", "Сидоров", "1")]
    new = [LessonEntry("Линал", "Сидоров", "2")]
    changes = compare_slot(10, 2, 3, old, new)
    assert any(c["type"] == "room_changed" for c in changes)
    rc = next(c for c in changes if c["type"] == "room_changed")
    assert rc["old_room"] == "1" and rc["new_room"] == "2"


def test_should_notify_next_week_all_slots() -> None:
    now = datetime(2026, 4, 8, 8, 0, 0)
    assert should_notify_slot(11, 0, 0, now, api_current_week=10) is True


def test_should_notify_other_week_false() -> None:
    now = datetime(2026, 4, 8, 8, 0, 0)
    assert should_notify_slot(9, 0, 0, now, api_current_week=10) is False


def test_should_notify_current_week_future_slot() -> None:
    now = datetime(2026, 4, 8, 10, 0, 0)
    assert should_notify_slot(10, 2, 2, now, api_current_week=10) is True


def test_should_notify_current_week_past_slot() -> None:
    now = datetime(2026, 4, 8, 15, 0, 0)
    assert should_notify_slot(10, 0, 0, now, api_current_week=10) is False


def test_build_changes_filters_by_should_notify() -> None:
    now = datetime(2026, 4, 8, 15, 0, 0)
    old_slots = [
        {
            "week_number": 10,
            "day_index": 0,
            "slot_index": 0,
            "lessons": [{"name": "A", "teacher": "T", "room": "1"}],
        }
    ]
    new_slots = [
        {
            "week_number": 10,
            "day_index": 0,
            "slot_index": 0,
            "lessons": [{"name": "B", "teacher": "T", "room": "1"}],
        }
    ]
    changes = build_changes(old_slots, new_slots, now=now, api_current_week=10)
    assert changes == []


def test_build_changes_detects_when_slot_notifiable() -> None:
    now = datetime(2026, 4, 8, 10, 0, 0)
    old_slots = [
        {
            "week_number": 10,
            "day_index": 2,
            "slot_index": 2,
            "lessons": [{"name": "X", "teacher": "Y", "room": "1"}],
        }
    ]
    new_slots = [
        {
            "week_number": 10,
            "day_index": 2,
            "slot_index": 2,
            "lessons": [{"name": "X", "teacher": "Y", "room": "2"}],
        }
    ]
    changes = build_changes(old_slots, new_slots, now=now, api_current_week=10)
    assert any(c["type"] == "room_changed" for c in changes)
