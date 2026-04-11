"""HTTP-клиент УлГТУ: сессия ЛК + запросы к API расписания."""

from __future__ import annotations

__all__ = [
    "UniversityApiClient",
    "UniversityClient",
    "UniversitySessionProvider",
]


def __getattr__(name: str):
    if name == "UniversityApiClient":
        from .api_client import UniversityApiClient

        return UniversityApiClient
    if name == "UniversitySessionProvider":
        from .session_provider import UniversitySessionProvider

        return UniversitySessionProvider
    if name == "UniversityClient":
        from .university_client import UniversityClient

        return UniversityClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
