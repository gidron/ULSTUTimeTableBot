from aiogram.fsm.state import State, StatesGroup


class SetGroupName(StatesGroup):
    group_name = State()
