from aiogram import Router

from .set_group_name import router as set_group_name_router
from .contact_developer import router as contact_developer_router
from .teacher_schedule import router as teacher_schedule_router

router = Router(name="user_state_handlers")

router.include_routers(
    set_group_name_router,
    contact_developer_router,
    teacher_schedule_router,
)

__all__ = ("router",)
