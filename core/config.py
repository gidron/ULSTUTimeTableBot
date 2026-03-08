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

    bot_link_text: str
    group_name: str = "УИДбд-21"

    request_timeout: float = 20.0
    verify_ssl: bool = True
    font_path: str | None = None

    pg_database: str
    pg_password: str
    pg_host: str
    pg_port: str
    pg_user: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
