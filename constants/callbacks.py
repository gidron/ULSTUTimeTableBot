from enum import StrEnum, unique


@unique
class CallbackConstants(StrEnum):
    SET_GROUP_NAME = "set_group_name"
    TOGGLE_NOTIFICATIONS = "toggle_notifications"
    CONTACT_DEVELOPER = "contact_developer"
