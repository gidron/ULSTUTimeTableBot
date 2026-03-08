import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from middlewares.throttling import ThrottlingMiddleware
from middlewares.check_user_is_active import CheckUserIsActiveMiddleware
from misc.routers import setup_routers
from core.config import get_settings
from core.logging import setup_logging
from database.connection import init_database

logger = logging.getLogger("default")


async def main() -> None:
    setup_logging()
    settings = get_settings()
    await init_database()

    logger.info("Starting bot...")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    redis_instance = Redis(host=settings.redis_host, port=int(settings.redis_port))
    storage = RedisStorage(redis_instance)
    dp = Dispatcher(storage=storage)
    dp.include_router(setup_routers())

    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(CheckUserIsActiveMiddleware())
    # dp.message.middleware(LastUserActivityMiddleware())

    logger.info("Bot initialized successfully, starting polling")

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot, close_bot_session=False)
    finally:
        logger.info("Shutting down bot")
        await dp.storage.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped successfully.")
    except ConnectionError:
        logger.info("Error during connecting to redis")
        raise SystemExit(1)
    except (TelegramNetworkError, SystemExit) as e:
        logger.warning(f"Bot stopped during an error: {e}")
        raise SystemExit(1)
