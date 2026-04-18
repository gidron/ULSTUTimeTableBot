from enum import StrEnum, unique


@unique
class CallbackConstants(StrEnum):
    PROFILE_ROOT = "profile_root"
    PROFILE_PAGE_GROUP = "profile_page_group"
    PROFILE_PAGE_SETTINGS = "profile_page_settings"
    PROFILE_PAGE_INFO = "profile_page_info"
    SET_GROUP_NAME = "set_group_name"
    TEACHER_SCHEDULE = "teacher_schedule"
    SCHEDULE_BY_DATE = "schedule_by_date"
    TOGGLE_NOTIFICATIONS = "toggle_notifications"
    TOGGLE_SCHEDULE_LAYOUT = "toggle_schedule_layout"
    CONTACT_DEVELOPER = "contact_developer"
