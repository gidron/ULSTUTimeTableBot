from enum import StrEnum, unique


@unique
class CommandText(StrEnum):
    START = "start"
    CURRENT_WEEK = "current"
    NEXT_WEEK = "next"
    SET_GROUP = "set_group"
    SUPPORT = "support"
    PROFILE = "profile"
    NEWSLETTER = "newsletter"
