from aiogram.filters.callback_data import CallbackData


class AcceptNewUserCallback(CallbackData, prefix="accept_new_user"):
    tg_id: int
    accept: bool


class PickSuggestedGroupCallback(CallbackData, prefix="pick_sgrp"):
    index: int


class PickSuggestedTeacherCallback(CallbackData, prefix="pick_stchr"):
    index: int


class AdminMenuCallback(CallbackData, prefix="adm_menu"):
    page: str  # root | stats | list | search | bcast


class AdminListCallback(CallbackData, prefix="adm_list"):
    flt: str  # all | active | banned | admins | nogroup
    page: int
    sort: str = "name"  # name | seen


class AdminUserCallback(CallbackData, prefix="adm_user"):
    tg_id: int
    back_flt: str
    back_page: int
    back_sort: str = "name"


class AdminActionCallback(CallbackData, prefix="adm_act"):
    tg_id: int
    action: str  # ban | admin | delete | dm | delete_confirm | delete_cancel
    back_flt: str
    back_page: int
    back_sort: str = "name"
