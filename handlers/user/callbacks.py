from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import CallbackQuery

from constants.callbacks import CallbackConstants
from keyboards.reply import cancel_kb
from misc.states import SetGroupName

router = Router(name="user_callbacks")


@router.callback_query(default_state, F.data == CallbackConstants.SET_GROUP_NAME)
async def set_group_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Введи название группы", reply_markup=cancel_kb)
    await state.set_state(SetGroupName.group_name)

