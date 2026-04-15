import json
import logging
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


def _parse_university_accounts_json(raw: str):
    """Парсит JSON-массив учёток; без переводов строк — на случай многострочного значения в одной строке env."""
    candidates = (raw, "".join(raw.splitlines()))
    last_exc: json.JSONDecodeError | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_exc = exc
    msg = (
        "UNIVERSITY_ACCOUNTS_JSON must be valid JSON. "
        "In .env the value is usually only one line: everything after '=' on the next lines "
        "is not part of UNIVERSITY_ACCOUNTS_JSON (so you may only get '[' and parsing fails). "
        "Put the whole array on a single line, e.g. "
        'UNIVERSITY_ACCOUNTS_JSON=[{"login":"u1","password":"p1"},{"login":"u2","password":"p2"}]'
    )
    raise ValueError(msg) from last_exc


class Settings(BaseSettings):
    bot_token: str

    # Можно задать только UNIVERSITY_ACCOUNTS_JSON; тогда пара ниже не обязательна.
    university_login: str = ""
    university_password: str = ""

    # JSON-массив: [{"login":"...","password":"..."}, ...]. Пусто — одна пара university_*.
    university_accounts_json: str | None = None
    # Общий round-robin между несколькими процессами (нужен подключённый Redis).
    university_accounts_use_redis_round_robin: bool = False
    university_accounts_redis_counter_key: str = "ulstu:univ_account_rr"

    login_url: str
    home_url: str
    timetable_api_url: str
    timetable_page_url: str
    current_week_api_url: str
    autocomplete_api_url: str

    bot_link_text: str

    developer_chat_id: int = 511952153

    request_timeout: float = 20.0
    verify_ssl: bool = True

    # Повторы при ConnectError / таймаутах (httpx к серверам УлГТУ).
    http_transient_attempts: int = 4
    http_retry_base_delay: float = 0.35

    font_path: str | None = None

    throttle_time: float = 5.0

    # Максимум одновременных полных циклов «API + рендер PNG»; 0 = без лимита.
    schedule_generation_concurrency: int = 8

    pg_database: str
    pg_password: str
    pg_host: str
    pg_port: int
    pg_user: str

    redis_host: str
    redis_port: int

    # Кэш PNG расписания в Redis (ключ: группа + scope + неделя + дата в schedule_timezone).
    schedule_cache_enabled: bool = False
    schedule_cache_ttl_seconds: int = 3600
    schedule_cache_key_prefix: str = "schedule_png"
    # IANA, например Europe/Samara — даты и подсветка «сегодня»; None = datetime.now() как раньше.
    schedule_timezone: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _ensure_university_credentials(self):
        for login, password in self.university_credentials_pool():
            if login.strip() and password:
                return self
        raise ValueError(
            "Задайте UNIVERSITY_LOGIN и UNIVERSITY_PASSWORD или UNIVERSITY_ACCOUNTS_JSON "
            "с хотя бы одной учётной записью с непустыми login и password."
        )

    def university_credentials_pool(self) -> list[tuple[str, str]]:
        raw = (self.university_accounts_json or "").strip()
        if not raw:
            return [(self.university_login, self.university_password)]
        # В .env значение часто обрывается на первой строке: остаётся только "[".
        if raw == "[":
            logger.warning(
                "UNIVERSITY_ACCOUNTS_JSON is only '[' — in .env the value must be "
                "one line after '='. Using university_login/university_password."
            )
            return [(self.university_login, self.university_password)]
        data = _parse_university_accounts_json(raw)
        if not isinstance(data, list):
            raise ValueError("UNIVERSITY_ACCOUNTS_JSON must be a JSON array")
        result: list[tuple[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(
                    "Each element of UNIVERSITY_ACCOUNTS_JSON must be an object"
                )
            login = item.get("login")
            password = item.get("password")
            if not isinstance(login, str) or not isinstance(password, str):
                raise ValueError('Each account must have string "login" and "password"')
            if login.strip() and password:
                result.append((login, password))
        if not result:
            return [(self.university_login, self.university_password)]
        return result


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
