"""Тесты нормализации слепка расписания."""

from __future__ import annotations

from services.schedule_changes.snapshot_builder import (
    build_two_week_slots,
    extract_week_slots,
    normalize_lesson_text,
    normalize_lessons,
    sort_slots_for_hash,
)


def test_normalize_lesson_text_collapses_whitespace() -> None:
    assert normalize_lesson_text("  Foo\n\tBar  ") == "foo bar"


def test_sort_slots_for_hash_order() -> None:
    slots = [
        {"week_number": 2, "day_index": 1, "slot_index": 0, "lessons": []},
        {"week_number": 1, "day_index": 5, "slot_index": 7, "lessons": []},
    ]
    sorted_slots = sort_slots_for_hash(slots)
    assert sorted_slots[0]["week_number"] == 1


def test_normalize_lessons_skips_empty_and_sorts() -> None:
    raw = [
        {"nameOfLesson": "B", "teacher": "T", "room": "1"},
        {"nameOfLesson": "A", "teacher": "T", "room": "1"},
        "not-a-dict",
    ]
    lessons = normalize_lessons(raw)
    assert [l.name for l in lessons] == ["a", "b"]


def test_extract_week_slots_flat_structure() -> None:
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [{"nameOfLesson": "X", "teacher": "Y", "room": "Z"}],
                ],
            }
        ]
    }
    slots = extract_week_slots(week_data, week_number=10)
    assert len(slots) == 1
    assert slots[0]["week_number"] == 10
    assert slots[0]["day_index"] == 0
    assert slots[0]["slot_index"] == 0
    assert slots[0]["lessons"][0]["name"] == "x"


def test_build_two_week_slots(minimal_timetable_payload: dict) -> None:
    slots = build_two_week_slots(minimal_timetable_payload, api_current_week=2)
    assert len(slots) >= 1
    keys = {(s["week_number"], s["day_index"], s["slot_index"]) for s in slots}
    assert len(keys) == len(slots)
