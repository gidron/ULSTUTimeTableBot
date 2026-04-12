from enum import StrEnum, unique


@unique
class ButtonText(StrEnum):
    CURRENT_WEEK = "Текущая неделя"
    NEXT_WEEK = "Следующая неделя"
    PROFILE = "⚙ Профиль"
    CONTACT_DEVELOPER = "✉️ Написать разработчику"
    CHANGE_GROUP = "🛠 Изменить группу"
    TEACHER_SCHEDULE = "👤 Расписание преподавателя"
    SCHEDULE_LAYOUT_DAYS_ROWS = "📅 Вид: дни строками"
    SCHEDULE_LAYOUT_DAYS_COLUMNS = "📅 Вид: дни столбцами"
    ENABLE_NOTIFICATIONS = "🔔 Включить уведомления"
    DISABLE_NOTIFICATIONS = "🔕 Выключить уведомления"
    DEATH = "💀"
    CANCEL = "❌ Отмена"
    ACCEPT_USER = "✅"
    CANCEL_USER = "❌"
