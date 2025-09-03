from aiogram.fsm.state import State, StatesGroup

class InterviewFSM(StatesGroup):
    choosing_vacancy = State()
    answering = State()
    followup = State()
    finished = State()
    awaiting_resume_link = State()  # ждём ссылку на резюме перед интервью
    hr_choose_vacancy = State()     # HR: выбор вакансии
    hr_fetching = State()           # HR: идёт подбор кандидатов
    awaiting_feedback = State()     # ждём обратную связь от кандидата