from aiogram.filters.callback_data import CallbackData


class AcceptNewUserCallback(CallbackData, prefix="accept_new_user"):
    tg_id: int
    accept: bool

