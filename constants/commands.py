from enum import StrEnum, unique


@unique
class CommandText(StrEnum):
    START = "start"
    CURRENT_WEEK = "current"
    NEXT_WEEK = "next"
    DAY = "day"
    SET_GROUP = "set_group"
    SUPPORT = "support"
    PROFILE = "profile"
    NEWSLETTER = "newsletter"
