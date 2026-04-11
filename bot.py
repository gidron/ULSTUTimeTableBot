import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage

from middlewares.last_user_activity import LastUserActivityMiddleware
from middlewares.throttling import ThrottlingMiddleware
from middlewares.check_user_is_active import CheckUserIsActiveMiddleware
from misc.routers import setup_routers
from core.config import get_settings
from core.logging import setup_logging
from core.redis import detach_redis, init_redis
from database.connection import init_database
from services.schedule_change_notifier import ScheduleChangeNotifier

logger = logging.getLogger("default")


async def main() -> None:
    setup_logging()
    settings = get_settings()
    await init_database()

    redis_client = await init_redis(settings.redis_host, int(settings.redis_port))
    storage = (
        RedisStorage(redis_client) if redis_client is not None else MemoryStorage()
    )

    logger.info("Starting bot")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)
    dp.include_router(setup_routers())

    dp.message.middleware(LastUserActivityMiddleware())
    dp.message.outer_middleware(ThrottlingMiddleware())
    dp.message.outer_middleware(CheckUserIsActiveMiddleware())

    await bot.delete_webhook(drop_pending_updates=True)
    notifier = ScheduleChangeNotifier()
    notifier_task = asyncio.create_task(notifier.run_forever(bot))

    try:
        logger.info("Bot initialized, starting polling")
        await dp.start_polling(bot, close_bot_session=False)
    finally:
        logger.info("Shutting down bot")
        await dp.storage.close()
        detach_redis()
        notifier_task.cancel()
        # await asyncio.gather(notifier_task, return_exceptions=True)
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
