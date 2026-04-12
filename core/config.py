from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str

    university_login: str
    university_password: str

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
