#!/usr/bin/env python3
"""Два параллельных get_week_image: время должно быть существенно меньше суммы двух по очереди."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import patch

# корень репозитория в PYTHONPATH при запуске: python scripts/verify_schedule_concurrency.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.schedule_service import ScheduleService  # noqa: E402


async def _fake_load(_self: ScheduleService):
    return (
        1,
        {"response": {"weeks": {"0": {"days": []}}}},
    )


async def _run_pair() -> float:
    async def one() -> None:
        svc = ScheduleService("TEST-GROUP")
        await svc.get_week_image("current")

    t0 = time.perf_counter()
    with patch.object(ScheduleService, "_load_schedule_payload", _fake_load):
        await asyncio.gather(one(), one())
    return time.perf_counter() - t0


async def _run_sequential() -> float:
    async def one() -> None:
        svc = ScheduleService("TEST-GROUP")
        await svc.get_week_image("current")

    t0 = time.perf_counter()
    with patch.object(ScheduleService, "_load_schedule_payload", _fake_load):
        await one()
        await one()
    return time.perf_counter() - t0


async def main() -> None:
    parallel_s = await _run_pair()
    sequential_s = await _run_sequential()
    print(f"parallel_two:    {parallel_s:.3f}s")
    print(f"sequential_two:  {sequential_s:.3f}s")
    if parallel_s >= sequential_s * 0.85:
        raise SystemExit(
            "Ожидалось, что параллельный прогон заметно быстрее последовательного "
            "(рендер в потоке не блокирует event loop)."
        )
    print("ok: parallel faster than sequential — render overlap works.")


if __name__ == "__main__":
    asyncio.run(main())
