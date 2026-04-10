import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from middlewares.last_user_activity import LastUserActivityMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.check_user_is_active import CheckUserIsActiveMiddleware
from misc.routers import setup_routers
from core.config import get_settings
from core.logging import setup_logging
from database.connection import init_database
from services.network import close_shared_session_provider
from services.schedule_change_notifier import ScheduleChangeNotifier

logger = logging.getLogger("default")


async def main() -> None:
    setup_logging()
    settings = get_settings()
    await init_database()

    logger.info("Starting bot")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    redis_instance = Redis(host=settings.redis_host, port=int(settings.redis_port))
    storage = RedisStorage(redis_instance)
    dp = Dispatcher(storage=storage)
    dp.include_router(setup_routers())

    dp.message.middleware(LastUserActivityMiddleware())
    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(CheckUserIsActiveMiddleware())

    logger.info("Bot initialized, starting polling")

    await bot.delete_webhook(drop_pending_updates=True)
    notifier = ScheduleChangeNotifier()
    notifier_task = asyncio.create_task(notifier.run_forever(bot))

    try:
        await dp.start_polling(bot, close_bot_session=False)
    finally:
        logger.info("Shutting down bot")
        await dp.storage.close()
        notifier_task.cancel()
        await asyncio.gather(notifier_task, return_exceptions=True)
        await close_shared_session_provider()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped successfully")
    except ConnectionError as exc:
        logger.error("Failed during connection | error=%s", exc)
        raise SystemExit(1) from exc
    except (TelegramNetworkError, SystemExit) as e:
        logger.warning("Bot stopped due to error | error=%s", e)
        raise SystemExit(1) from e
