from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.chat_action import ChatActionSender

from constants.commands import CommandText
from core.config import get_settings
from database.models import User
from handlers.user.state_handlers.contact_developer import prompt_contact_developer
from handlers.user.state_handlers.set_group_name import prompt_set_group
from keyboards.builders import accept_new_user_kb
from keyboards.inline import profile_inline_kb
from keyboards.reply import main_menu_user_kb
from constants.buttons_text import ButtonText as BT
from misc.states import SetGroupName
from misc.user_admin_card import format_user_admin_card_html
from services.schedule import ScheduleService
from services.schedule.parser import TimetableParseError
from services.schedule_changes.demo_changes import build_demo_notify_message

router = Router(name="user_commands")


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    user = message.from_user
    tg_id = user.id
    full_name = user.full_name
    username = user.username

    user = await User.get_or_none(tg_id=tg_id)

    if user is None:
        user = await User.create(
            tg_id=tg_id, name=full_name, username=username, is_active=False
        )
        settings = get_settings()
        await message.bot.send_message(
            chat_id=settings.developer_chat_id,
            text=format_user_admin_card_html(
                title="Новый пользователь!",
                tg_id=tg_id,
                full_name=full_name,
                username=username,
            ),
            reply_markup=accept_new_user_kb(tg_id),
        )

    if user.is_active and not user.group_name:
        await message.answer(
            f"<b>{full_name}, добро пожаловать в нашего бота!</b>\n"
            f"Перед тем как начать им пользоваться тебе необходимо "
            f"указать группу, в которой ты учишься.\n"
            f"Пример - <b>УИДбд-21</b>"
        )
        await state.set_state(SetGroupName.group_name)
    elif user.is_active and user.group_name:
        await message.answer(
            f"С возвращением, <b>{full_name}</b>!", reply_markup=main_menu_user_kb
        )


@router.message(F.text.in_([BT.CURRENT_WEEK, BT.NEXT_WEEK]))
@router.message(Command(CommandText.CURRENT_WEEK))
@router.message(Command(CommandText.NEXT_WEEK))
async def show_week(message: Message, command: CommandObject | None = None):
    tg_id = message.from_user.id
    cmd = command.command if command else None
    user = await User.get(tg_id=tg_id)

    service = ScheduleService(user.group_name)
    message_to_delete = await message.answer("⏳ Расписание генерируется...")

    if message.text == BT.CURRENT_WEEK or cmd == CommandText.CURRENT_WEEK:
        week_kind = "current"
        caption = "Текущая неделя"
    else:
        week_kind = "next"
        caption = "Следующая неделя"

    async with ChatActionSender(
        bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5
    ):
        try:
            image_bytes, filename, week_range = await service.get_week_image(week_kind)
        except TimetableParseError:
            await message.answer(
                "Расписание для указанной недели пока что отсутствует.\n"
                "Попробуй позднее еще раз."
            )
        else:
            caption = (
                f"📚 Расписания для группы <b>{user.group_name}</b>\n"
                + "🕰️ "
                + caption
                + " "
                + f"<b>{week_range}</b>"
                if week_range
                else "Расписание недели"
            )

            photo = BufferedInputFile(image_bytes, filename=filename)
            await message.answer_photo(photo=photo, caption=caption, reply_markup=main_menu_user_kb)

    await message_to_delete.delete()


@router.message(F.text == BT.PROFILE)
@router.message(Command(CommandText.PROFILE))
async def profile(message: Message):
    user = await User.get(tg_id=message.from_user.id)
    group_line = (
        f"<b>{user.group_name}</b>"
        if user.group_name
        else "<i>не указана — без группы расписание недоступно</i>"
    )
    if user.notify_by_change:
        notify_bullet = (
            f"• ⚠️ <b>[ТЕСТ]</b> {BT.DISABLE_NOTIFICATIONS} — отключить сообщения, когда на сайте "
            "появится новая версия расписания твоей группы. "
            "Сейчас уведомления <b>включены</b>."
        )
    else:
        notify_bullet = (
            f"• ️⚠️ <b>[ТЕСТ]</b> {BT.ENABLE_NOTIFICATIONS} — получать сообщения при обновлении "
            "расписания на сайте для твоей группы. "
            "Сейчас уведомления <b>выключены</b>."
        )

    text = (
        "<b>⚙ Профиль</b>\n\n"
        f"📚 <b>Группа</b>\n{group_line}\n\n"
        "<b>Что делают кнопки ниже</b>\n"
        f"• {BT.CHANGE_GROUP} — указать или сменить учебную группу "
        f"(как в официальном расписании, например <code>УИДбд-21</code>).\n"
        f"{notify_bullet}\n"
        f"• {BT.CONTACT_DEVELOPER} — отправить вопрос или сообщение разработчику \n\n"
        "<i>Нажми нужную кнопку 👇</i>"
    )
    await message.answer(
        text,
        reply_markup=profile_inline_kb(user.notify_by_change),
    )


@router.message(Command(CommandText.SUPPORT))
async def support_command(message: Message, state: FSMContext):
    await prompt_contact_developer(message, state)


@router.message(Command("id"))
async def get_id(message: Message):
    return await message.answer(str(message.from_user.id))


@router.message(Command("preview_notify"))
async def preview_notify(message: Message):
    """Случайные «старый/новый» слепки → тот же текст, что у реального уведомления."""
    user = await User.get_or_none(tg_id=message.from_user.id)
    if user is None or not user.is_admin:
        await message.answer("Команда доступна только администратору.")
        return

    group = (user.group_name or "Демо-группа").strip()
    text = build_demo_notify_message(group)
    await message.answer(text)


@router.message(Command(CommandText.SET_GROUP))
async def set_group_command(message: Message, state: FSMContext):
    await prompt_set_group(message, state)
