from aiogram.fsm.state import State, StatesGroup


class RegisterUserForm(StatesGroup):
    group_name = State()

