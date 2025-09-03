from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from vacancies import VACANCIES
from keyboards import hr_vacancy_keyboard, hr_candidate_actions, invite_keyboard
from services.resume_fetcher import search_and_fetch
from services.hr_classifier_service import classify_bulk, classify_one
from storage import USER_STATES, InterviewState, save_state
from states import InterviewFSM
from typing import Any, List, Dict, Optional
from dataclasses import field
from bs4 import BeautifulSoup
from keyboards import InlineKeyboardBuilder
import os
from aiogram.types import FSInputFile
from services.file_resume_parser import FileResumeParser

router = Router()

@router.message(Command("start_hr"))
async def start_hr(m: Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔎 Подобрать кандидатов", callback_data="hr_search")
    kb.button(text=" Загрузить резюме", callback_data="hr_upload_menu")
    kb.button(text="📋 Мои резюме", callback_data="hr_my_resumes")
    kb.adjust(1)
    
    await m.answer(
        " <b>HR-модуль</b>\n\n"
        "Выберите действие:\n"
        "• 🔎 Подобрать кандидатов — поиск на hh.ru\n"
        "•  Загрузить резюме — анализ файлов RTF/DOCX\n"
        "• 📋 Мои резюме — просмотр загруженных резюме",
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data == "hr_search")
async def on_hr_search(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(
        "Выберите вакансию для подбора кандидатов:",
        reply_markup=hr_vacancy_keyboard().as_markup()
    )
    await state.set_state(InterviewFSM.hr_choose_vacancy)

@router.callback_query(F.data == "hr_upload_menu")
async def on_hr_upload_menu(c: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for v in VACANCIES.values():
        kb.button(text=v.title, callback_data=f"hr_upload:{v.key}")
    kb.adjust(1)
    
    await c.message.edit_text(
        "Выберите вакансию для анализа резюме:",
        reply_markup=kb.as_markup()
    )

@router.callback_query(F.data == "hr_my_resumes")
async def on_hr_my_resumes(c: CallbackQuery):
    s = USER_STATES.get(c.from_user.id)
    if not s or not hasattr(s, 'file_resumes') or not s.file_resumes:
        await c.answer("У вас пока нет загруженных резюме", show_alert=True)
        return
    
    await c.message.edit_text("📋 <b>Ваши загруженные резюме:</b>", parse_mode="HTML")
    
    for safe_file_id, resume_data in s.file_resumes.items():
        cv_data = resume_data["cv_data"]
        analysis = resume_data["analysis"]
        mp = analysis.get('match_percent', 0)
        
        status_emoji = "🟢" if mp >= 75 else "🟡" if mp >= 50 else "🔴"
        
        kb = InlineKeyboardBuilder()
        kb.button(text="📋 Отчёт", callback_data=f"report_file_{safe_file_id}")
        kb.button(text=" Удалить", callback_data=f"delete_file_{safe_file_id}")
        kb.adjust(2)
        
        await c.message.answer(
            f"{status_emoji} <b>{cv_data['title']}</b> — {mp}%\n"
            f" {resume_data['file_name']}",
            parse_mode="HTML",
            reply_markup=kb.as_markup()
        )

@router.callback_query(F.data.startswith("hr_vac:"))
async def on_hr_choose(c: CallbackQuery, state: FSMContext):
    vac_key = c.data.split(":",1)[1]
    if vac_key not in VACANCIES:
        await c.answer("Неизвестная вакансия", show_alert=True)
        return
    s = USER_STATES.get(c.from_user.id) or InterviewState()
    s.vacancy_key = vac_key
    USER_STATES[c.from_user.id] = s
    save_state(c.from_user.id)
    vac = VACANCIES[vac_key]
    await c.message.edit_text(
        f"Вакансия: <b>{vac.title}</b>\n{vac.description}\n\nНажмите, чтобы подобрать кандидатов.",
        parse_mode="HTML",
        reply_markup=hr_candidate_actions(vac_key).as_markup()
    )
    await state.set_state(InterviewFSM.hr_fetching)

INVITE_THRESHOLD = 75  # можно вынести в config

@router.callback_query(F.data.startswith("hr_fetch:"))
async def on_hr_fetch(c: CallbackQuery, state):
    vac_key = c.data.split(":",1)[1]

    # 1) СРАЗУ подтверждаем callback, до любых долгих операций
    try:
        await c.answer()
    except Exception:
        pass

    try:
        await c.answer()
    except Exception:
        pass
    vac = VACANCIES[vac_key]
    await c.message.edit_text(f"Ищу кандидатов под: <b>{vac.title}</b> … Это может занять до 1–2 минут.", parse_mode="HTML")

    cvs = await search_and_fetch(vac.title)
    results = await classify_bulk(vac, cvs)

    s = USER_STATES.get(c.from_user.id) or InterviewState()
    s.hr_candidates = []  # перезапишем
    suitable, unsuitable = [], []

    for cv, res in zip(cvs, results):
        entry = {
            "url": cv.get("url",""),
            "title": cv.get("title","") or "Кандидат",
            "experience": (cv.get("experience","") or "")[:280],
            "skills": cv.get("skills",""),
            "match_percent": int(res.get("match_percent", 0) or 0),
            "decision": (res.get("decision", "hold") or "").lower(),
            "fit": bool(res.get("fit", False)),
            "rationale": res.get("rationale","") or "",
        }
        s.hr_candidates.append(entry)
        ok = entry["fit"] or entry["decision"] == "go" or entry["match_percent"] >= INVITE_THRESHOLD
        (suitable if ok else unsuitable).append(entry)

    USER_STATES[c.from_user.id] = s
    save_state(c.from_user.id)

    # Заголовок
    await c.message.answer("<b>Подбор кандидатов завершён</b>", parse_mode="HTML")

    # Подходят — карточками
    if suitable:
        await c.message.answer("<b>Подходят:</b>", parse_mode="HTML")
        for i, entry in enumerate(s.hr_candidates):
            if entry not in suitable:
                continue
            kb = InlineKeyboardBuilder()
            kb.button(text="🔗 Открыть резюме", url=entry["url"])
            kb.button(text="📨 Пригласить", callback_data=f"invite:{i}")
            kb.adjust(2)
            lines = [
                f"<b>{entry['title']}</b> — {entry['match_percent']}%",
                f"<a href=\"{entry['url']}\">Резюме</a>",
            ]
            if entry["skills"]:
                lines.append(f"Навыки: {entry['skills'][:200]}")
            if entry["experience"]:
                lines.append(f"Опыт: {entry['experience']}")
            await c.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup())

    # Не подходят — списком с причинами и ссылкой
    if unsuitable:
        lines = ["<b>Не подходят:</b>"]
        for entry in unsuitable:
            why = entry['rationale']
            why = (why[:140] + "…") if why and len(why) > 140 else (why or "не соответствует требованиям")
            lines.append(f"- <a href=\"{entry['url']}\">{entry['title']}</a> — {why}")
        await c.message.answer("\n".join(lines), parse_mode="HTML")

    # await c.answer()

@router.callback_query(F.data.startswith("invite:"))
async def on_invite(c: CallbackQuery):
    # СРАЗУ подтверждаем
    try:
        await c.answer()
    except Exception:
        pass

    try:
        idx = int(c.data.split(":",1)[1])
    except Exception:
        await c.answer("Некорректная кнопка", show_alert=True)
        return
    s = USER_STATES.get(c.from_user.id)
    if not s or idx < 0 or idx >= len(s.hr_candidates):
        await c.answer("Кандидат не найден", show_alert=True)
        return
    cand = s.hr_candidates[idx]
    await c.message.answer(f"Приглашение отправлено кандидату: <a href=\"{cand['url']}\">{cand['title']}</a>", parse_mode="HTML")
    # await c.answer()

@router.callback_query(F.data.startswith("hr_upload:"))
async def on_hr_upload(c: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки загрузки резюме"""
    vac_key = c.data.split(":",1)[1]
    if vac_key not in VACANCIES:
        await c.answer("Неизвестная вакансия", show_alert=True)
        return
    
    s = USER_STATES.get(c.from_user.id) or InterviewState()
    s.vacancy_key = vac_key
    USER_STATES[c.from_user.id] = s
    save_state(c.from_user.id)
    
    vac = VACANCIES[vac_key]
    await c.message.edit_text(
        f"Загрузите файл резюме в формате RTF или DOCX для вакансии: <b>{vac.title}</b>\n\n"
        f"Поддерживаемые форматы:\n"
        f"• RTF (.rtf)\n"
        f"• DOCX (.docx)\n\n"
        f"Файл будет проанализирован и сопоставлен с требованиями вакансии.",
        parse_mode="HTML"
    )
    await state.set_state(InterviewFSM.hr_fetching)

@router.message(InterviewFSM.hr_fetching, F.document)
async def on_file_upload(m: Message, state: FSMContext):
    """Обработка загруженного файла резюме"""
    s = USER_STATES.get(m.from_user.id)
    if not s or not s.vacancy_key:
        await m.answer("Сначала выберите вакансию командой /start_hr")
        return
    
    # Проверяем формат файла
    file_ext = os.path.splitext(m.document.file_name)[1].lower()
    if file_ext not in ['.rtf', '.docx']:
        await m.answer("Поддерживаются только файлы в формате RTF или DOCX")
        return
    
    await m.answer("🔍 Обрабатываю файл резюме...")
    
    try:
        # Скачиваем файл
        file_path = f"downloads/{m.document.file_id}_{m.document.file_name}"
        os.makedirs("downloads", exist_ok=True)
        
        print(f"Скачивание файла: {m.document.file_name}")
        await m.bot.download(m.document, file_path)
        print(f"Файл сохранен: {file_path}")
        
        # Проверяем размер файла
        if not os.path.exists(file_path):
            await m.answer("❌ Ошибка при скачивании файла")
            return
        
        file_size = os.path.getsize(file_path)
        print(f"Размер файла: {file_size} байт")
        
        if file_size == 0:
            await m.answer("❌ Файл пустой или поврежден")
            return
        
        # Парсим файл
        cv_data = FileResumeParser.parse_file(file_path)
        
        if not cv_data:
            await m.answer("❌ Не удалось обработать файл. Проверьте формат и содержимое.")
            return
        
        print(f"Данные резюме извлечены: {cv_data['title']}")
        
        # Анализируем резюме
        vac = VACANCIES[s.vacancy_key]
        res = await classify_one(vac, cv_data)
        
        mp = int(res.get("match_percent", 0) or 0)
        dec = (res.get("decision", "hold") or "").lower()
        rat = res.get("rationale", "")
        
        # Определяем статус
        status_emoji = "🟢" if mp >= 75 or dec == "go" else "🟡" if mp >= 50 else "🔴"
        status_text = "Подходит" if mp >= 75 or dec == "go" else "Рассмотреть" if mp >= 50 else "Не подходит"
        
        # Формируем ответ
        response_lines = [
            f"{status_emoji} <b>Анализ резюме: {cv_data['title']}</b>",
            f" Совпадение: <b>{mp}%</b>",
            f" Статус: <b>{status_text}</b>",
            f"🎯 Решение: <b>{dec.upper()}</b>",
        ]
        
        if rat:
            response_lines.append(f"💡 Обоснование: {rat}")
        
        if cv_data['skills']:
            response_lines.append(f" Навыки: {cv_data['skills']}")
        
        if cv_data['experience']:
            response_lines.append(f"💼 Опыт: {cv_data['experience'][:200]}...")
        
        # Создаем безопасный ID для файла (используем только цифры и буквы)
        safe_file_id = m.document.file_id.replace('-', '').replace('_', '')[:16]
        
        # Создаем клавиатуру для действий
        kb = InlineKeyboardBuilder()
        if mp >= 75 or dec == "go":
            kb.button(text="✅ Пригласить на интервью", callback_data=f"invite_file_{safe_file_id}")
        elif mp >= 50:
            kb.button(text="🤔 Рассмотреть детально", callback_data=f"review_file_{safe_file_id}")
        
        kb.button(text="❌ Отклонить", callback_data=f"reject_file_{safe_file_id}")
        kb.button(text="📋 Подробный отчёт", callback_data=f"report_file_{safe_file_id}")
        kb.adjust(1)
        
        await m.answer("\n".join(response_lines), parse_mode="HTML", reply_markup=kb.as_markup())
        
        # Сохраняем данные в состояние
        if not hasattr(s, 'file_resumes'):
            s.file_resumes = {}
        
        s.file_resumes[safe_file_id] = {
            "cv_data": cv_data,
            "analysis": res,
            "file_name": m.document.file_name,
            "file_path": file_path,
            "upload_time": m.date.isoformat(),
            "original_file_id": m.document.file_id
        }
        
        USER_STATES[m.from_user.id] = s
        save_state(m.from_user.id)
        
    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")
        import traceback
        traceback.print_exc()
        await m.answer(f"❌ Ошибка при обработке файла: {str(e)}")
    finally:
        # Очищаем временный файл
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Временный файл удален: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")

@router.callback_query(F.data.startswith("invite_file_"))
async def on_invite_file(c: CallbackQuery):
    """Приглашение кандидата из файла"""
    try:
        await c.answer()
    except Exception:
        pass
    
    safe_file_id = c.data.split("invite_file_", 1)[1]
    s = USER_STATES.get(c.from_user.id)
    
    if not s or not hasattr(s, 'file_resumes') or safe_file_id not in s.file_resumes:
        await c.answer("Данные о резюме не найдены", show_alert=True)
        return
    
    resume_data = s.file_resumes[safe_file_id]
    cv_data = resume_data["cv_data"]
    
    await c.message.answer(
        f"✅ Приглашение отправлено кандидату: <b>{cv_data['title']}</b>\n"
        f"Файл: {resume_data['file_name']}",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("reject_file_"))
async def on_reject_file(c: CallbackQuery):
    """Отклонение кандидата из файла"""
    try:
        await c.answer()
    except Exception:
        pass
    
    safe_file_id = c.data.split("reject_file_", 1)[1]
    s = USER_STATES.get(c.from_user.id)
    
    if not s or not hasattr(s, 'file_resumes') or safe_file_id not in s.file_resumes:
        await c.answer("Данные о резюме не найдены", show_alert=True)
        return
    
    resume_data = s.file_resumes[safe_file_id]
    cv_data = resume_data["cv_data"]
    
    await c.message.answer(
        f"❌ Кандидат отклонён: <b>{cv_data['title']}</b>\n"
        f"Файл: {resume_data['file_name']}",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("review_file_"))
async def on_review_file(c: CallbackQuery):
    """Детальный просмотр кандидата"""
    try:
        await c.answer()
    except Exception:
        pass
    
    safe_file_id = c.data.split("review_file_", 1)[1]
    s = USER_STATES.get(c.from_user.id)
    
    if not s or not hasattr(s, 'file_resumes') or safe_file_id not in s.file_resumes:
        await c.answer("Данные о резюме не найдены", show_alert=True)
        return
    
    resume_data = s.file_resumes[safe_file_id]
    cv_data = resume_data["cv_data"]
    analysis = resume_data["analysis"]
    
    # Создаем клавиатуру для финального решения
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Пригласить", callback_data=f"invite_file_{safe_file_id}")
    kb.button(text="❌ Отклонить", callback_data=f"reject_file_{safe_file_id}")
    kb.button(text="📋 Полный отчёт", callback_data=f"report_file_{safe_file_id}")
    kb.adjust(2, 1)
    
    review_text = [
        f"🔍 <b>Детальный анализ кандидата</b>",
        f" {cv_data['title']}",
        f"📊 Совпадение: {analysis.get('match_percent', 0)}%",
        f"",
        f"<b>Сильные стороны:</b>",
    ]
    
    if analysis.get('strengths'):
        for strength in analysis['strengths']:
            review_text.append(f"✅ {strength}")
    else:
        review_text.append("Не указаны")
    
    review_text.append(f"\n<b>Пробелы:</b>")
    if analysis.get('gaps'):
        for gap in analysis['gaps']:
            review_text.append(f"⚠️ {gap}")
    else:
        review_text.append("Не выявлены")
    
    await c.message.edit_text("\n".join(review_text), parse_mode="HTML", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("report_file_"))
async def on_report_file(c: CallbackQuery):
    """Подробный отчёт по файлу"""
    try:
        await c.answer()
    except Exception:
        pass
    
    safe_file_id = c.data.split("report_file_", 1)[1]
    s = USER_STATES.get(c.from_user.id)
    
    if not s or not hasattr(s, 'file_resumes') or safe_file_id not in s.file_resumes:
        await c.answer("Данные о резюме не найдены", show_alert=True)
        return
    
    resume_data = s.file_resumes[safe_file_id]
    cv_data = resume_data["cv_data"]
    analysis = resume_data["analysis"]
    
    report_lines = [
        f"<b>Подробный отчёт по резюме</b>",
        f"Кандидат: {cv_data['title']}",
        f"Файл: {resume_data['file_name']}",
        f"",
        f"<b>Анализ:</b>",
        f"Совпадение: {analysis.get('match_percent', 0)}%",
        f"Решение: {analysis.get('decision', 'hold').upper()}",
        f"Подходит: {'Да' if analysis.get('fit', False) else 'Нет'}",
    ]
    
    if analysis.get('rationale'):
        report_lines.append(f"Обоснование: {analysis['rationale']}")
    
    if analysis.get('strengths'):
        strengths = ', '.join(analysis['strengths'])
        report_lines.append(f"Сильные стороны: {strengths}")
    
    if analysis.get('gaps'):
        gaps = ', '.join(analysis['gaps'])
        report_lines.append(f"Пробелы: {gaps}")
    
    report_lines.extend([
        f"",
        f"<b>Данные резюме:</b>",
        f"Навыки: {cv_data.get('skills', 'Не указаны')}",
        f"Опыт: {cv_data.get('experience', 'Не указан')[:300]}...",
    ])
    
    await c.message.answer("\n".join(report_lines), parse_mode="HTML")

@router.callback_query(F.data.startswith("delete_file_"))
async def on_delete_file(c: CallbackQuery):
    """Удаление файла резюме"""
    try:
        await c.answer()
    except Exception:
        pass
    
    safe_file_id = c.data.split("delete_file_", 1)[1]
    s = USER_STATES.get(c.from_user.id)
    
    if not s or not hasattr(s, 'file_resumes') or safe_file_id not in s.file_resumes:
        await c.answer("Резюме не найдено", show_alert=True)
        return
    
    resume_data = s.file_resumes[safe_file_id]
    cv_data = resume_data["cv_data"]
    
    # Удаляем из состояния
    del s.file_resumes[safe_file_id]
    USER_STATES[c.from_user.id] = s
    save_state(c.from_user.id)
    
    # Удаляем файл если он существует
    if os.path.exists(resume_data['file_path']):
        try:
            os.remove(resume_data['file_path'])
        except:
            pass
    
    await c.message.edit_text(f" Резюме <b>{cv_data['title']}</b> удалено", parse_mode="HTML")