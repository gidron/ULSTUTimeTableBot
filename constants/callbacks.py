from enum import StrEnum, unique


@unique
class CallbackConstants(StrEnum):
    SET_GROUP_NAME = "set_group_name"
    TEACHER_SCHEDULE = "teacher_schedule"
    SCHEDULE_BY_DATE = "schedule_by_date"
    TOGGLE_NOTIFICATIONS = "toggle_notifications"
    TOGGLE_SCHEDULE_LAYOUT = "toggle_schedule_layout"
    CONTACT_DEVELOPER = "contact_developer"
