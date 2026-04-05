from aiogram import Router

from .set_group_name import router as set_group_name_router

router = Router(name="user_state_handlers")

router.include_routers(set_group_name_router)

__all__ = ("router",)
