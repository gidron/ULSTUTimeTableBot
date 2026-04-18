from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("admin_audit")


def log_admin_action(
    *,
    actor_tg_id: int,
    action: str,
    target_tg_id: int | None = None,
    **details: Any,
) -> None:
    """Append a structured line to the admin audit log."""
    parts = [f"actor={actor_tg_id}", f"action={action}"]
    if target_tg_id is not None:
        parts.append(f"target={target_tg_id}")
    for key, value in details.items():
        parts.append(f"{key}={value}")
    logger.info(" | ".join(parts))
