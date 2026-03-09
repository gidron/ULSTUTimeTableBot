import socket
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV = ".env"
hostname = socket.gethostname()

if hostname != "gidron-laptop":
    ENV = ".env.prod"


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

    request_timeout: float = 20.0
    verify_ssl: bool = True
    font_path: str | None = None

    throttle_time: float = 5.0

    pg_database: str
    pg_password: str
    pg_host: str
    pg_port: int
    pg_user: str

    redis_host: str
    redis_port: int

    model_config = SettingsConfigDict(
        env_file=ENV,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
