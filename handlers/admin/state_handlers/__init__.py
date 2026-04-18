from aiogram import Router

from .dm import router as dm_router
from .search import router as search_router

router = Router(name="admin_state_handlers")

router.include_routers(
    search_router,
    dm_router,
)

__all__ = ("router",)
