from enum import StrEnum, unique


@unique
class ButtonText(StrEnum):
    CURRENT_WEEK = "Текущая неделя"
    NEXT_WEEK = "Следующая неделя"
    PROFILE = "⚙ Профиль"
    DEATH = "💀"
