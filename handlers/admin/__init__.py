from aiogram import Router
from .commands import router as command_router

router = Router(name="admin_handlers")

router.include_routers(command_router)

__all__ = ("router",)
