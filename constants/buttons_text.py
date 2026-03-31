from enum import StrEnum, unique


@unique
class ButtonText(StrEnum):
    CURRENT_WEEK = "Текущая неделя"
    NEXT_WEEK = "Следующая неделя"
    PROFILE = "⚙ Профиль"
    CHANGE_GROUP = "🛠 Изменить группу"
    ENABLE_NOTIFICATIONS = "🔔 Включить уведомления"
    DISABLE_NOTIFICATIONS = "🔕 Выключить уведомления"
    DEATH = "💀"
    CANCEL = "❌ Отмена"
    ACCEPT_USER = "✅"
    CANCEL_USER = "❌"
