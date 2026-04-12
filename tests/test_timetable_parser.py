"""Тесты разбора и нормализации ответа API расписания."""

from __future__ import annotations

import pytest

from services.schedule.parser import TimetableParseError, TimetableParser


def test_get_weeks_returns_items() -> None:
    payload = {
        "response": {
            "weeks": {
                "0": {"days": []},
                "1": {"days": []},
            }
        }
    }
    weeks = TimetableParser.get_weeks(payload)
    assert len(weeks) == 2
    assert {k for k, _ in weeks} == {"0", "1"}


def test_get_weeks_raises_on_empty() -> None:
    with pytest.raises(TimetableParseError, match="response.weeks"):
        TimetableParser.get_weeks({"response": {"weeks": {}}})

    with pytest.raises(TimetableParseError):
        TimetableParser.get_weeks({"response": {}})


def test_pick_week_current_with_match() -> None:
    payload = {
        "response": {
            "weeks": {
                "1": {"days": [{"day": 0, "lessons": []}]},
                "2": {"days": []},
            }
        }
    }
    key, data = TimetableParser.pick_week(payload, "current", current_week_number=3)
    assert key == "2"
    assert "days" in data


def test_pick_week_current_falls_back_to_first_sorted() -> None:
    payload = {"response": {"weeks": {"5": {"days": []}, "10": {"days": []}}}}
    key, _ = TimetableParser.pick_week(payload, "current", current_week_number=99)
    assert key == "5"


def test_pick_week_next_success() -> None:
    payload = {"response": {"weeks": {"3": {"days": []}}}}
    key, data = TimetableParser.pick_week(payload, "next", current_week_number=3)
    assert key == "3"
    assert data == {"days": []}


def test_pick_week_next_without_current_raises() -> None:
    payload = {"response": {"weeks": {"0": {}}}}
    with pytest.raises(TimetableParseError, match="without current_week_number"):
        TimetableParser.pick_week(payload, "next", current_week_number=None)


def test_pick_week_next_missing_raises() -> None:
    payload = {"response": {"weeks": {"0": {}}}}
    with pytest.raises(TimetableParseError, match="not available"):
        TimetableParser.pick_week(payload, "next", current_week_number=5)


def test_pick_week_unknown_kind() -> None:
    with pytest.raises(TimetableParseError, match="Unknown week_kind"):
        TimetableParser.pick_week(
            {"response": {"weeks": {"0": {}}}}, "invalid", current_week_number=1
        )


def test_normalize_week_empty_slots_and_highlight() -> None:
    week_data = {"days": []}
    out = TimetableParser.normalize_week(
        "3", week_data, group_name="ИВТ-101", highlight_day_index=2
    )
    assert out["group_name"] == "ИВТ-101"
    assert out["schedule_title_prefix"] == "Расписание группы:"
    assert out["week_number"] == "3"
    assert len(out["days"]) == 6
    assert out["days"][2]["is_current_day"] is True
    assert out["days"][0]["is_current_day"] is False
    for d in out["days"]:
        assert len(d["slots"]) == 8
        assert all(s == "" for s in d["slots"])


def test_normalize_week_custom_title_prefix() -> None:
    week_data = {"days": []}
    out = TimetableParser.normalize_week(
        "1",
        week_data,
        group_name="Иванов И И",
        schedule_title_prefix="Расписание преподавателя:",
    )
    assert out["schedule_title_prefix"] == "Расписание преподавателя:"


def test_normalize_week_teacher_mode_puts_group_before_lesson() -> None:
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [
                        {
                            "group": "УИДбд-21",
                            "nameOfLesson": "пр. Менеджмент",
                            "teacher": "Волкова Е А",
                            "room": "2-223",
                        }
                    ],
                ]
                + [[] for _ in range(7)],
            }
        ]
    }
    out = TimetableParser.normalize_week(
        "0",
        week_data,
        group_name="Волкова Е А",
        include_study_group_in_slots=True,
    )
    slot0 = out["days"][0]["slots"][0]
    lines = slot0.split("\n")
    assert lines[0] == "УИДбд-21"
    assert "Менеджмент" in slot0
    assert "2-223" in slot0
    assert "Волкова" not in slot0


def test_normalize_week_formats_slot() -> None:
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [
                        {
                            "nameOfLesson": "Матан",
                            "teacher": "Иванов",
                            "room": "101",
                        }
                    ],
                ]
                + [[] for _ in range(7)],
            }
        ]
    }
    out = TimetableParser.normalize_week("0", week_data, group_name="G")
    slot0 = out["days"][0]["slots"][0]
    assert "Матан" in slot0
    assert "Иванов" in slot0
    assert "101" in slot0


def test_normalize_week_teacher_mode_multi_groups_on_one_line() -> None:
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [
                        {
                            "group": "УИДбд-21",
                            "nameOfLesson": "пр. А",
                            "teacher": "Петров П П",
                            "room": "1-1",
                        },
                        {
                            "group": "УИДбд-22",
                            "nameOfLesson": "лек. Б",
                            "teacher": "Петров П П",
                            "room": "1-2",
                        },
                    ],
                ]
                + [[] for _ in range(7)],
            }
        ]
    }
    out = TimetableParser.normalize_week(
        "0",
        week_data,
        group_name="Петров П П",
        include_study_group_in_slots=True,
    )
    text = out["days"][0]["slots"][0]
    assert text.startswith("УИДбд-21 УИДбд-22")
    assert "пр. А" in text and "лек. Б" in text
    assert "Петров" not in text


def test_normalize_week_student_mode_duplicate_discipline_merged() -> None:
    """Две записи API на одну пару с разными группами, но одинаковым предметом — один блок."""
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [
                        {
                            "group": "Мбд-21",
                            "nameOfLesson": "лек. Менеджмент",
                            "teacher": "Т Уч",
                            "room": "2-223",
                        },
                        {
                            "group": "МКбд-21",
                            "nameOfLesson": "лек. Менеджмент",
                            "teacher": "Т Уч",
                            "room": "2-223",
                        },
                    ],
                ]
                + [[] for _ in range(7)],
            }
        ]
    }
    out = TimetableParser.normalize_week("0", week_data, group_name="G")
    text = out["days"][0]["slots"][0]
    assert text.count("лек. Менеджмент") == 1
    assert text.startswith("Мбд-21 МКбд-21")


def test_normalize_week_student_mode_multi_groups_on_one_line() -> None:
    week_data = {
        "days": [
            {
                "day": 0,
                "lessons": [
                    [
                        {
                            "group": "Гр-1",
                            "nameOfLesson": "пр. А",
                            "teacher": "Т1",
                            "room": "101",
                        },
                        {
                            "group": "Гр-2",
                            "nameOfLesson": "лек. Б",
                            "teacher": "Т2",
                            "room": "102",
                        },
                    ],
                ]
                + [[] for _ in range(7)],
            }
        ]
    }
    out = TimetableParser.normalize_week("0", week_data, group_name="G")
    text = out["days"][0]["slots"][0]
    assert text.startswith("Гр-1 Гр-2")
    assert "пр. А" in text and "Т1" in text
    assert "лек. Б" in text and "Т2" in text


def test_normalize_week_multiple_lessons_in_slot() -> None:
    week_data = {
        "days": [
            {
                "day": 1,
                "lessons": [
                    [],
                    [
                        {"nameOfLesson": "A", "teacher": "", "room": "1"},
                        {"nameOfLesson": "B", "teacher": "T", "room": "2"},
                    ],
                ]
                + [[] for _ in range(6)],
            }
        ]
    }
    out = TimetableParser.normalize_week("0", week_data, group_name="G")
    text = out["days"][1]["slots"][1]
    assert "A" in text and "B" in text
