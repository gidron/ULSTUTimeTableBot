from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery

from constants.callbacks import CallbackConstants
from database.models import User
from keyboards.inline import profile_inline_kb
from keyboards.factories import AcceptNewUserCallback
from keyboards.reply import cancel_kb
from misc.states import SetGroupName

router = Router(name="user_callbacks")


@router.callback_query(default_state, F.data == CallbackConstants.SET_GROUP_NAME)
async def set_group_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введи название группы", reply_markup=cancel_kb)
    await state.set_state(SetGroupName.group_name)


@router.callback_query(default_state, F.data == CallbackConstants.TOGGLE_NOTIFICATIONS)
async def toggle_notifications(callback: CallbackQuery):
    user = await User.get(tg_id=callback.from_user.id)
    user.notify_by_change = not user.notify_by_change
    await user.save()

    toggle_text = "включены" if user.notify_by_change else "выключены"
    await callback.answer(f"Уведомления {toggle_text}")
    await callback.message.edit_reply_markup(
        reply_markup=profile_inline_kb(user.notify_by_change)
    )


@router.callback_query(default_state, AcceptNewUserCallback.filter())
async def accept_new_user(
    callback: CallbackQuery, callback_data: AcceptNewUserCallback
):
    tg_id = callback_data.tg_id
    is_accept = callback_data.accept

    if is_accept:
        user = await User.get(tg_id=tg_id)
        user.is_active = True
        await user.save()

        await callback.bot.send_message(
            chat_id=tg_id, text="Тебя добавили. Введи /start"
        )

    await callback.answer("Успешно")
    await callback.message.edit_reply_markup(callback.inline_message_id, None)
    await callback.message.edit_text("✔" + callback.message.text)
