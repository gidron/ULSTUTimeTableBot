"""Уведомления пользователю после принятия в бот (разработчик или админ)."""

from __future__ import annotations

from aiogram import Bot

_ADDED_STICKER_FILE_ID = (
    "CAACAgIAAxkBAAICFGnWk6zi3fLhHHqc5gxikWrEcmrKAAKcWwACl2dxSMeEVHqNXTnbOwQ"
)
_ADDED_TEXT = "Тебя добавили. Введи /start"


async def notify_user_added(bot: Bot, chat_id: int) -> None:
    await bot.send_sticker(chat_id=chat_id, sticker=_ADDED_STICKER_FILE_ID)
    await bot.send_message(chat_id=chat_id, text=_ADDED_TEXT)
