from aiogram import Router
from .commands import router as user_commands_router
from .day_schedule import router as day_schedule_router
from .state_handlers import router as state_handlers_router
from .callbacks import router as user_callback_router

router = Router(name="user_handlers")

router.include_routers(
    user_callback_router,
    state_handlers_router,
    day_schedule_router,
    user_commands_router,
)

__all__ = ("router",)
