from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from aiogram.utils.chat_action import ChatActionSender

from database.models import User, ScheduleSnapshot, ScheduleChangeDigest
from keyboards.builders import accept_new_user_kb
from keyboards.inline import profile_inline_kb
from keyboards.reply import main_menu_user_kb
from constants.buttons_text import ButtonText as BT
from misc.states import SetGroupName
from services.data_parser import TimetableParseError
from services.schedule_change_notifier import ScheduleChangeNotifier
from services.schedule_service import ScheduleService

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
        await message.bot.send_message(
            chat_id=511952153,
            text=f"Новый пользователь!\n"
            f"ID: <code>{tg_id}</code>\n"
            f"Full name: {full_name}\n"
            f"username: @{username}",
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
async def show_current_week(message: Message):
    tg_id = message.from_user.id
    user = await User.get(tg_id=tg_id)

    service = ScheduleService(user.group_name)
    message_to_delete = await message.answer("⏳ Расписание генерируется...")

    if message.text == BT.CURRENT_WEEK:
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
            await message.answer_photo(photo=photo, caption=caption)

    await message_to_delete.delete()


@router.message(F.text == BT.PROFILE)
async def profile(message: Message):
    user = await User.get(tg_id=message.from_user.id)
    await message.answer(
        "Выбери опцию:", reply_markup=profile_inline_kb(user.notify_by_change)
    )


@router.message(Command("id"))
async def get_id(message: Message):
    return await message.answer(str(message.from_user.id))


@router.message(Command("test_notify_run"))
async def test_notify_run(message: Message):
    user = await User.get_or_none(tg_id=message.from_user.id)
    if user is None or not user.is_admin:
        await message.answer("Команда доступна только администратору.")
        return

    await message.answer("Запускаю проверку уведомлений вручную...")
    notifier = ScheduleChangeNotifier()
    await notifier.check_and_notify(message.bot)
    await message.answer("Проверка завершена.")


@router.message(Command("test_notify_reset"))
async def test_notify_reset(message: Message):
    user = await User.get_or_none(tg_id=message.from_user.id)
    if user is None or not user.is_admin:
        await message.answer("Команда доступна только администратору.")
        return

    if not user.group_name:
        await message.answer("У вас не указана группа.")
        return

    deleted_snapshot = await ScheduleSnapshot.filter(
        group_name=user.group_name
    ).delete()
    deleted_digests = await ScheduleChangeDigest.filter(
        group_name=user.group_name
    ).delete()
    await message.answer(
        f"Сброс выполнен для группы {user.group_name}:\n"
        f"- snapshot: {deleted_snapshot}\n"
        f"- digests: {deleted_digests}"
    )
