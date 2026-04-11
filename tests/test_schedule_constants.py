"""Тесты констант расписания (время начала пары)."""

from __future__ import annotations

from services.schedule.constants import pair_slot_start_time


def test_pair_slot_start_time_first_slot() -> None:
    assert pair_slot_start_time(0) == (8, 30)


def test_pair_slot_start_time_last_defined_slot() -> None:
    assert pair_slot_start_time(7) == (19, 30)


def test_pair_slot_start_time_out_of_range_upper() -> None:
    assert pair_slot_start_time(8) == (0, 0)
    assert pair_slot_start_time(99) == (0, 0)
