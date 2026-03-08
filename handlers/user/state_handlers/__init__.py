from aiogram import Router

from .register_user_form import router as register_user_form_router

router = Router(name="user_state_handlers")

router.include_routers(
    register_user_form_router
)

__all__ = ("router", )
