import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

from middlewares.throttling import ThrottlingMiddleware
from misc.routers import setup_routers
from core.config import get_settings
from core.logging import setup_logging

logger = logging.getLogger("default")


async def main() -> None:
    setup_logging()
    settings = get_settings()

    logger.info("Starting bot...")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(setup_routers())

    dp.message.outer_middleware(ThrottlingMiddleware())

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
