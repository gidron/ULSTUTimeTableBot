from aiogram import Router

from .callbacks import router as callbacks_router
from .commands import router as commands_router
from .state_handlers import router as state_handlers_router

router = Router(name="admin_handlers")

router.include_routers(
    callbacks_router,
    state_handlers_router,
    commands_router,
)

__all__ = ("router",)
