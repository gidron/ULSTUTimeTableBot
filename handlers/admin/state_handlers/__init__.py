from aiogram import Router

from .add_user import router as add_user_router
from .dm import router as dm_router
from .search import router as search_router

router = Router(name="admin_state_handlers")

router.include_routers(
    search_router,
    add_user_router,
    dm_router,
)

__all__ = ("router",)
