from aiogram.fsm.state import State, StatesGroup


class SetGroupName(StatesGroup):
    group_name = State()


class TeacherSchedule(StatesGroup):
    teacher_query = State()


class DaySchedule(StatesGroup):
    waiting_date = State()


class ContactDeveloper(StatesGroup):
    message = State()
