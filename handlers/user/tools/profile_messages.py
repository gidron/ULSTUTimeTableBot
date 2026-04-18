"""HTML-тексты панели профиля и вложенных экранов (Telegram, parse_mode HTML)."""

from database.models import User
from constants.buttons_text import ButtonText as BT
from constants.schedule_layout import ScheduleLayout, parse_schedule_layout


def _group_line(user: User) -> str:
    if user.group_name:
        return f"<b>{user.group_name}</b>"
    return "<i>не указана — без группы расписание недоступно</i>"


def _layout_status_phrase(user: User) -> str:
    if parse_schedule_layout(user.schedule_layout) == ScheduleLayout.HORIZONTAL:
        return "дни строками"
    return "дни столбцами"


def _notify_bullet(user: User) -> str:
    if user.notify_by_change:
        return (
            f"• <i>{BT.DISABLE_NOTIFICATIONS}</i> — отключить сообщения, когда на сайте "
            "появится новая версия расписания твоей группы. "
            "Сейчас уведомления <b>включены</b>."
        )
    return (
        f"• <i>{BT.ENABLE_NOTIFICATIONS}</i> — получать сообщения при обновлении "
        "расписания на сайте для твоей группы. "
        "Сейчас уведомления <b>выключены</b>."
    )


def build_profile_root_text(user: User) -> str:
    return (
        "<b>⚙ Панель профиля</b>\n\n"
        f"📚 <b>Группа</b>\n{_group_line(user)}\n\n"
        "Выбери раздел ниже 👇"
    )


def build_profile_group_page_text(user: User) -> str:
    return (
        "<b>📚 Группа и расписание</b>\n\n"
        f"📚 <b>Группа</b>\n{_group_line(user)}\n\n"
        "<b>Что делают кнопки</b>\n"
        f"• <i>{BT.CHANGE_GROUP}</i> — указать или сменить учебную группу "
        f"(как в официальном расписании, например <code>УИДбд-21</code>).\n"
        f"• <i>{BT.TEACHER_SCHEDULE}</i> — посмотреть расписание преподавателя на текущую и "
        "следующую неделю (поиск по фамилии и инициалам, как на сайте).\n"
        f"• <i>{BT.SCHEDULE_BY_DATE}</i> — ввести дату <code>ДД.ММ</code> или <code>/day 15.02</code> "
        "(в границах семестра; ориентировочно по чередованию недель).\n\n"
        f"<i>{BT.PROFILE_BACK} — вернуться к панели</i>"
    )


def build_profile_settings_page_text(user: User) -> str:
    return (
        "<b>🔧 Настройки</b>\n\n"
        f"Вид расписания сейчас: <b>{_layout_status_phrase(user)}</b>.\n\n"
        "<b>Что делают кнопки</b>\n"
        f"{_notify_bullet(user)}\n"
        f"• <i>{BT.SCHEDULE_LAYOUT_DAYS_ROWS} / {BT.SCHEDULE_LAYOUT_DAYS_COLUMNS}</i> — как показывать "
        "расписание: дни строками (по умолчанию) или столбцами.\n\n"
        f"<i>{BT.PROFILE_BACK} — вернуться к панели</i>"
    )


def build_profile_info_page_text() -> str:
    return (
        "<b>ℹ️ Информация</b>\n\n"
        "Расписание берётся с официального сайта вуза. Внизу чата — быстрый доступ к текущей и "
        "следующей неделе; здесь — группа, преподаватели, день по дате, уведомления и вид таблицы.\n\n"
        "<b>Связь</b>\n"
        f"• <i>{BT.CONTACT_DEVELOPER}</i> — отправить вопрос или сообщение разработчику.\n\n"
        f"<i>{BT.PROFILE_BACK} — вернуться к панели</i>"
    )
