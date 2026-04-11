"""Тесты стабильного хеширования payload."""

from __future__ import annotations

from services.schedule_changes.hashing import hash_payload


def test_hash_payload_stable_for_key_order() -> None:
    a = {"z": 1, "a": {"y": 2, "b": 3}}
    b = {"a": {"b": 3, "y": 2}, "z": 1}
    assert hash_payload(a) == hash_payload(b)


def test_hash_payload_changes_with_value() -> None:
    assert hash_payload({"x": 1}) != hash_payload({"x": 2})


def test_hash_payload_deterministic() -> None:
    data = {"items": [1, 2, {"k": "v"}]}
    assert hash_payload(data) == hash_payload(data)
