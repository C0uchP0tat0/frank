from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from keyboards import vacancy_keyboard
from states import InterviewFSM
from storage import USER_STATES, InterviewState, save_state


router = Router()


@router.message(CommandStart())
async def on_start(m: Message, state: FSMContext):
    USER_STATES[m.from_user.id] = InterviewState()
    save_state()
    text = (
    "Привет! Я ИИ-ассистент для собеседований. Можем общаться голосом или текстом.\n\n"
    "Выберите вакансию, по которой хотите пройти короткое интервью:"
    )
    await m.answer(text, reply_markup=vacancy_keyboard().as_markup())
    await state.set_state(InterviewFSM.choosing_vacancy)


# from aiogram import Router
# from aiogram.filters import CommandStart
# from aiogram.types import Message
# from keyboards import vacancy_keyboard

# router = Router()

# @router.message(CommandStart())
# async def on_start(m: Message):
#     text = (
#         "Привет! Я ИИ-ассистент для собеседований 👋\n\n"
#         "Выберите вакансию, по которой хотите пройти интервью:"
#     )
#     await m.answer(text, reply_markup=vacancy_keyboard().as_markup())