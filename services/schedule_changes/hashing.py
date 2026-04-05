"""Стабильное хеширование JSON-структур для слепков и digest уведомлений."""

from __future__ import annotations

import hashlib
import json


def hash_payload(payload: object) -> str:
    """SHA-256 от JSON с сортировкой ключей (ensure_ascii=False)."""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
