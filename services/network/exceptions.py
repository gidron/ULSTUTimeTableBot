"""Исключения клиента университета (авторизация и JSON API)."""


class UniversityClientError(Exception):
    """Базовая ошибка при работе с ЛК или API УлГТУ."""


class UniversityAuthError(UniversityClientError):
    """Не удалось войти или получить cookie для time.ulstu.ru."""


class UniversityApiError(UniversityClientError):
    """Ошибка или неверный формат ответа JSON API расписания."""
