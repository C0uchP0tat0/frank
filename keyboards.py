from aiogram.utils.keyboard import InlineKeyboardBuilder
from vacancies import VACANCIES

def vacancy_keyboard():
    kb = InlineKeyboardBuilder()
    for v in VACANCIES.values():
        kb.button(text=v.title, callback_data=f"vac:{v.key}")
    kb.adjust(1)
    return kb

def hr_vacancy_keyboard():
    kb = InlineKeyboardBuilder()
    for v in VACANCIES.values():
        kb.button(text=v.title, callback_data=f"hr_vac:{v.key}")
    kb.adjust(1)
    return kb

def hr_candidate_actions(vac_key: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Подобрать кандидатов", callback_data=f"hr_fetch:{vac_key}")
    kb.button(text=" Загрузить резюме", callback_data=f"hr_upload:{vac_key}")
    kb.adjust(1)
    return kb

def invite_keyboard(url: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="📨 Пригласить на этап", callback_data=f"invite:{url}".encode('utf-8'))
    return kb

def report_keyboard(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Скачать отчёт", callback_data=f"report:{user_id}")
    return kb