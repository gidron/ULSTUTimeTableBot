from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.chat_action import ChatActionSender

from database.models import User
from keyboards.factories import PickSuggestedGroupCallback
from keyboards.inline import group_suggestions_inline_kb
from keyboards.reply import main_menu_user_kb
from misc.states import SetGroupName
from constants.buttons_text import ButtonText as BT
from services.network import UniversityClient


router = Router(name="user_state_handlers_register_user_form")


async def _complete_group_setup(message: Message, tg_id: int, group_name: str, state: FSMContext) -> None:
    user = await User.get(tg_id=tg_id)
    user.group_name = group_name
    await user.save()
    await state.update_data(suggested_groups=None)
    await message.answer(
        "Группа сохранена! В дальнейшем ты сможешь изменить ее в настройках.",
        reply_markup=main_menu_user_kb,
    )
    await state.set_state()


@router.message(SetGroupName.group_name, F.text == BT.CANCEL)
async def cancel_input(message: Message, state: FSMContext):
    await state.update_data(suggested_groups=None)
    await message.answer("Отменено", reply_markup=main_menu_user_kb)
    await state.set_state()


@router.callback_query(SetGroupName.group_name, PickSuggestedGroupCallback.filter())
async def pick_suggested_group(
    callback: CallbackQuery,
    callback_data: PickSuggestedGroupCallback,
    state: FSMContext,
):
    data = await state.get_data()
    groups: list[str] = data.get("suggested_groups") or []
    idx = callback_data.index
    if idx < 0 or idx >= len(groups):
        await callback.answer("Список устарел. Введи название группы ещё раз.", show_alert=True)
        return

    await callback.answer()
    group_name = groups[idx]
    await callback.message.delete()
    await _complete_group_setup(callback.message, callback.from_user.id, group_name, state)


@router.message(SetGroupName.group_name, F.text)
async def user_set_group_name(message: Message, state: FSMContext):
    user = message.from_user
    tg_id = user.id
    group_name = message.text.strip()

    if len(group_name) < 3:
        await message.answer("Название группы должно быть не короче 3 символов.")
        return

    async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, initial_sleep=0.5):
        message_to_delete = await message.answer("🔍 Идет поиск группы...")

        async with UniversityClient(group_name) as client:
            groups_autocomplete = await client.find_groups()

            if group_name not in groups_autocomplete:
                await message_to_delete.delete()
                if not groups_autocomplete:
                    await message.answer(
                        "Такой группы не найдено. Попробуй другое название (не короче 3 символов)."
                    )
                    return

                await state.update_data(suggested_groups=groups_autocomplete)
                await message.answer(
                    "Такой группы нет в списке. Выбери одну из найденных:",
                    reply_markup=group_suggestions_inline_kb(groups_autocomplete),
                )
                return

        await message_to_delete.delete()

    await state.update_data(suggested_groups=None)
    await _complete_group_setup(message, tg_id, group_name, state)


@router.message(SetGroupName.group_name, ~F.text)
async def invalid_user_set_group_name(message: Message):
    await message.answer("Введи текст!")
