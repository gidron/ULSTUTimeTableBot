from aiogram import Router

from handlers import router as handler_router


def setup_routers() -> Router:
    router = Router()
    router.include_router(handler_router)
    return router
