from aiogram import Router
from .commands import router as user_commands_router

router = Router(name="user_handlers")

router.include_routers(
    user_commands_router
)

__all__ = ("router", )


