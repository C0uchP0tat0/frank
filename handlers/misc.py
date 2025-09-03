from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from vacancies import VACANCIES
from storage import USER_STATES, InterviewState, save_state


router = Router()


@router.message(Command("vacancies"))
async def list_vacancies(m: Message):
    text = "Доступные вакансии:\n" + "\n".join([f"• {v.title}" for v in VACANCIES.values()])
    await m.answer(text)


@router.message(Command("cancel"))
async def cancel(m: Message, state):
    await state.clear()
    USER_STATES[m.from_user.id] = InterviewState()
    save_state(m.from_user.id)
    await m.answer("Окей, интервью сброшено. Нажмите /start, чтобы начать заново.")