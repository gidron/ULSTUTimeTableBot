#!/usr/bin/env python3
"""Ручной замер TTL серверной сессии ЛК УлГТУ / time.ulstu.ru.

Логинимся один раз через UniversitySessionProvider и в цикле опрашиваем current-week API
с теми же cookies, пока ответ не превратится в редирект на форму логина (401/403 или HTML
с маркерами формы входа). Печатаем, сколько секунд сессия жила после авторизации.

Запуск из корня репозитория:
    python scripts/probe_session_ttl.py --login <login> --password <pass> --group <group> \
        --step-seconds 60 --max-hours 12

Учётные данные можно не передавать — тогда возьмутся из .env (UNIVERSITY_LOGIN / PASSWORD
или первый аккаунт из UNIVERSITY_ACCOUNTS_JSON).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import httpx  # noqa: E402

from core.config import get_settings  # noqa: E402
from services.network.session_provider import UniversitySessionProvider  # noqa: E402

logger = logging.getLogger("probe_session_ttl")


_AUTH_MARKERS = ("auth/login", "form", "password")


def _response_requires_reauth(response: httpx.Response) -> bool:
    """Повторяет логику UniversityApiClient._response_requires_reauth без зависимости от него."""
    if response.status_code in {401, 403}:
        return True

    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        return False

    if "html" not in content_type:
        return False

    text = response.text.lower()
    return any(marker in text for marker in _AUTH_MARKERS)


async def _probe_once(client: httpx.AsyncClient, url: str) -> tuple[bool, str]:
    """True — сессия ещё жива; False — нужна новая авторизация."""
    try:
        response = await client.get(
            url,
            headers={"Accept": "application/json, text/plain, */*"},
        )
    except httpx.HTTPError as exc:
        return True, f"transient http error: {exc!r}"

    if _response_requires_reauth(response):
        return False, (
            f"reauth required | status={response.status_code} "
            f"| content_type={response.headers.get('Content-Type', '')}"
        )

    if response.status_code != 200:
        return True, (
            f"non-200 (but not reauth) | status={response.status_code} "
            f"| content_type={response.headers.get('Content-Type', '')}"
        )

    try:
        data = response.json()
    except ValueError:
        return False, "non-json body on 200 (likely login page)"

    return True, f"ok | response={data.get('response')!r}"


async def run(args: argparse.Namespace) -> int:
    settings = get_settings()

    login = args.login or settings.university_login
    password = args.password or settings.university_password
    if not login or not password:
        pool = settings.university_credentials_pool()
        if pool:
            login, password = pool[0]

    if not login or not password:
        logger.error(
            "No credentials available: pass --login/--password or set UNIVERSITY_LOGIN/PASSWORD"
        )
        return 2

    group = args.group
    step = max(5, int(args.step_seconds))
    max_seconds = int(args.max_hours * 3600)

    logger.info(
        "Starting session TTL probe | login=%s | group=%s | step=%ss | max=%ss",
        login,
        group,
        step,
        max_seconds,
    )

    provider = UniversitySessionProvider(
        group=group,
        login=login,
        password=password,
        enable_account_failover=False,
    )

    async with provider:
        client = await provider.get_authorized_client()
        authorized_at = time.monotonic()
        logger.info("Authorized; starting poll loop")

        deadline = authorized_at + max_seconds
        iteration = 0
        last_alive_elapsed = 0.0

        while True:
            iteration += 1
            elapsed = time.monotonic() - authorized_at
            alive, detail = await _probe_once(client, settings.current_week_api_url)
            logger.info(
                "probe #%s | t+%ss | alive=%s | %s",
                iteration,
                int(elapsed),
                alive,
                detail,
            )

            if not alive:
                print(
                    "\nSession expired.\n"
                    f"  login:               {login}\n"
                    f"  last alive (t+):     {int(last_alive_elapsed)}s\n"
                    f"  first dead (t+):     {int(elapsed)}s\n"
                    f"  probe step:          {step}s\n"
                    f"  recommended TTL:     ~{int(last_alive_elapsed * 0.8)}s "
                    "(80% of last-known-alive, round down)\n"
                )
                return 0

            last_alive_elapsed = elapsed

            if time.monotonic() >= deadline:
                print(
                    "\nMax probe duration reached without session expiry.\n"
                    f"  login:               {login}\n"
                    f"  observed alive for:  >= {int(elapsed)}s\n"
                    f"  probe step:          {step}s\n"
                    "  consider increasing --max-hours to find the real TTL.\n"
                )
                return 0

            await asyncio.sleep(step)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--login", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument(
        "--group",
        required=True,
        help="Любая существующая группа УлГТУ (нужна для шага открытия страницы расписания).",
    )
    parser.add_argument("--step-seconds", type=int, default=60)
    parser.add_argument("--max-hours", type=float, default=12.0)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
