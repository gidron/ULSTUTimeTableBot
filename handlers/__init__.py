from aiogram import Router
from .admin import router as admin_router
from .user import router as user_router

router = Router(name="user_handlers")

router.include_routers(
    admin_router,
    user_router,
)

__all__ = ("router", )
