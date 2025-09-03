import asyncio
import os, logging
import random
from aiogram import Router, F, Bot
from aiogram.enums.poll_type import PollType
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, PollAnswer, FSInputFile
from services.llm_clarifier_service import ClarifierService
from services.tts_service import TTSService
from services.voice_clone_service import VoiceCloneService
from vacancies import VACANCIES
from states import InterviewFSM
from storage import USER_STATES, InterviewState, save_state
from keyboards import report_keyboard
from services.audio_service import AudioService
from services.llm_service import LLMService
from services.analyzer_service import AnalyzerService
import json
from services.resume_fetcher import fetch_text, parse_resume
from services.hr_classifier_service import classify_one
import httpx
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from dataclasses import field


router = Router()


@router.message(InterviewFSM.awaiting_resume_link, F.text)
async def on_resume_link(m: Message, state: FSMContext):
    s = USER_STATES.get(m.from_user.id)
    if not s or not s.vacancy_key:
        await m.answer("Нажмите /start, чтобы начать.")
        return
    url = (m.text or "").strip()
    try:
        async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent":"Mozilla/5.0"}) as client:
            html = await fetch_text(client, url)
        cv = parse_resume(html) or {"title":"", "experience":"", "skills":""}
        cv["url"] = url
    except Exception as e:
        await m.answer(f"Не удалось получить резюме: {e}\nПопробуйте другую ссылку или обратитесь позже.")
        # Блокируем продолжение интервью при отсутствии валидного резюме
        await state.clear()
        USER_STATES[m.from_user.id] = InterviewState()
        save_state(m.from_user.id)
        return

    vac = VACANCIES[s.vacancy_key]
    res = await classify_one(vac, cv)
    mp = int(res.get("match_percent", 0) or 0)
    dec = (res.get("decision", "hold") or "").lower()
    rat = res.get("rationale", "")

    # Жёсткий отсев: reject или слишком низкий матчинг
    # REJECT_THRESHOLD = 65
    # if dec == "reject" or mp < REJECT_THRESHOLD:
    #     reason = (rat[:300] + "…") if rat and len(rat) > 300 else (rat or "не соответствует требованиям вакансии")
    #     await m.answer(
    #         "К сожалению, мы не можем продолжить: резюме не соответствует требованиям вакансии.\n"
    #         f"Причина: {reason}\n\nВы можете выбрать другую вакансию командой /start или /start_hr."
    #     )
    #     await state.clear()
    #     USER_STATES[m.from_user.id] = InterviewState()
    #     save_state(m.from_user.id)
    #     return

    await m.answer(
        f"Предварительная оценка резюме: {mp}% — {dec}\n{(rat[:400]+'…') if rat and len(rat)>400 else rat or ''}\n\nНачнём интервью."
    )

    await ask_next_question(m, s)
    await state.set_state(InterviewFSM.answering)

async def ask_next_question(m: Message, s: InterviewState):
    vac = VACANCIES[s.vacancy_key]
    if s.q_index >= len(vac.questions):
        try:
            await m.answer_video_note(FSInputFile("media/frank/2_come_back.mp4"))
        except:
            await m.answer("Спасибо! Опираясь на Ваши ответы подготовлю дополнительные вопросы, вернусь к Вам через минуту")
        await finalize_and_report(m, s)
        return
    
    q = vac.questions[s.q_index]
    text_q = f"Вопрос {s.q_index+1}/{len(vac.questions)}:\n ` {q} `"

    # 1) пробуем отдать предзаписанный видео-кружок
    base_dir = f"media/questions/{s.vacancy_key}"
    idx = s.q_index + 1
    candidates = [f"{base_dir}/{idx}.mp4", f"{base_dir}/{idx}.webm"]
    video_path = next((p for p in candidates if os.path.exists(p)), None)

    if video_path:
        try:
            await m.answer_video_note(FSInputFile(video_path))
            await m.answer(text_q, parse_mode="MarkdownV2")
            return
        except Exception as e:
            logging.exception(f"Не удалось отправить видео-кружок: {e}")

    # 2) fallback: голос (если хотите оставить) + подпись текстом
    try:
        tts_file = await VoiceCloneService.process_text(q)
        if isinstance(tts_file, str) and not tts_file.startswith("Ошибка") and os.path.exists(tts_file):
            await m.answer_voice(FSInputFile(tts_file))
            await m.answer(text_q, parse_mode="MarkdownV2")
            return
    except Exception as e:
        logging.exception(f"TTS/VoiceClone ошибка: {e}")

    # 3) если ничего не вышло — просто текст
    await m.answer(text_q, parse_mode="MarkdownV2")


@router.callback_query(F.data.startswith("vac:"))
async def on_choose_vacancy(c: CallbackQuery, state: FSMContext):
    vac_key = c.data.split(":", 1)[1]
    if vac_key not in VACANCIES:
        await c.answer("Неизвестная вакансия", show_alert=True)
        return
    s = USER_STATES.get(c.from_user.id) or InterviewState()
    s.vacancy_key = vac_key
    s.q_index = 0
    s.answers = []
    s.history = []
    USER_STATES[c.from_user.id] = s
    save_state(c.from_user.id)

    vac = VACANCIES[vac_key]

    await c.message.edit_text(
        f"Вы выбрали: <b>{vac.title}</b>\n\n{vac.description}\n\nНачинаем интервью!",
        parse_mode="HTML"
    )
    try:
        await c.message.answer_video_note(FSInputFile("media/frank/1_frank_hi.mp4"))
        await asyncio.sleep(10)
    except:
        ...
    await ask_next_question(c.message, s)
    await state.set_state(InterviewFSM.answering)
    
    

@router.message(InterviewFSM.answering, F.content_type == "voice")
async def on_voice_answer(m: Message, state: FSMContext):
    s = USER_STATES.get(m.from_user.id)
    if not s or not s.vacancy_key:
        await m.answer("Нажмите /start, чтобы начать.")
        return

    # если сейчас ждём ответ на уточняющий вопрос — примем голос, распознаем и обработаем
    if s.pending_followup_qindex is not None:
        try:
            file = await m.bot.get_file(m.voice.file_id)
            local_path = f"downloads/{m.voice.file_unique_id}.oga"
            os.makedirs("downloads", exist_ok=True)
            await m.bot.download_file(file.file_path, destination=local_path)
            text = await AudioService.process_audio_file(local_path)
        except Exception as e:
            logging.exception("ASR error")
            await m.answer(f"Не удалось распознать голос: {e}")
            return
        await on_inline_followup_text(m, state, override_text=text)
        return

    # обычный поток (не уточнение)
    try:
        file = await m.bot.get_file(m.voice.file_id)
        local_path = f"downloads/{m.voice.file_unique_id}.oga"
        os.makedirs("downloads", exist_ok=True)
        await m.bot.download_file(file.file_path, destination=local_path)
        text = await AudioService.process_audio_file(local_path)
    except Exception as e:
        logging.exception("ASR error")
        await m.answer(f"Не удалось распознать голос: {e}")
        return
    await handle_answer_text(m, text)


@router.message(InterviewFSM.answering, F.text)
async def on_text_answer(m: Message, state: FSMContext):
    s = USER_STATES.get(m.from_user.id)
    # если ждём инлайн-уточнение — не перехватываем здесь
    if s and s.pending_followup_qindex is not None:
        await on_inline_followup_text(m, state)
        return
    await handle_answer_text(m, m.text or "")


async def handle_answer_text(m: Message, text: str):
    s = USER_STATES.get(m.from_user.id)
    vac = VACANCIES[s.vacancy_key]
    curr_idx = s.q_index

    user_answer = (text or "").strip()
    s.answers.append(user_answer)
    s.history.append({"role": "user", "content": user_answer})
    USER_STATES[m.from_user.id] = s
    save_state()

    q_text = vac.questions[curr_idx]
    check = await ClarifierService.clarify_single(q_text, user_answer)
    need = bool(check.get("need_followup"))
    fup = (check.get("followup_open") or "").strip()

    if need and fup:
        s.pending_followup_qindex = curr_idx
        s.pending_followup_text = fup
        USER_STATES[m.from_user.id] = s
        save_state()

        # озвучиваем уточняющий вопрос
        try:
            vfile = await VoiceCloneService.process_text(fup)
            if isinstance(vfile, str) and os.path.exists(vfile):
                await m.answer_voice(FSInputFile(vfile))
        except Exception as e:
            logging.exception(f"Ошибка озвучки уточнения: {e}")

        await m.answer(f"Уточним: \n ` {fup} ` ", parse_mode="MarkdownV2")
        return

    s.q_index += 1
    USER_STATES[m.from_user.id] = s
    save_state()
    await ask_next_question(m, s)


async def on_inline_followup_text(m: Message, state: FSMContext, override_text: str | None = None):
    s = USER_STATES.get(m.from_user.id)
    if not s or s.pending_followup_qindex is None:
        await m.answer("Нажмите /start, чтобы начать.")
        return

    idx = s.pending_followup_qindex
    extra = (override_text if override_text is not None else (m.text or "")).strip()

    try:
        base = s.answers[idx]
        combined = base + (f"\nУточнение: {extra}" if extra else "")
        s.answers[idx] = combined
    except Exception:
        pass

    if extra:
        s.history.append({"role": "user", "content": f"(Уточнение к ответу {idx+1}) {extra}"})

    s.pending_followup_qindex = None
    s.pending_followup_text = None
    s.q_index += 1
    USER_STATES[m.from_user.id] = s
    save_state()

    await ask_next_question(m, s)




# async def handle_answer_text(m: Message, text: str):
#     s = USER_STATES.get(m.from_user.id)
#     vac = VACANCIES[s.vacancy_key]
#     curr_idx = s.q_index

#     # запоминаем исходный ответ в историю и список ответов (пока без инлайн-дополнения)
#     user_answer = (text or "").strip()
#     s.answers.append(user_answer)
#     s.history.append({"role": "user", "content": user_answer})
#     USER_STATES[m.from_user.id] = s
#     save_state()

#     # проверяем полноту текущего ответа
#     q_text = vac.questions[curr_idx]
#     check = await ClarifierService.clarify_single(q_text, user_answer)
#     need = bool(check.get("need_followup"))
#     fup = (check.get("followup_open") or "").strip()

#     if need and fup:
#         # задаём уточняющий вопрос и ждём ответ
#         s.pending_followup_qindex = curr_idx
#         s.pending_followup_text = fup
#         USER_STATES[m.from_user.id] = s
#         save_state()
#         await m.answer(f"Уточним: {fup}")
#         # остаёмся на этом же вопросе, не инкрементируем q_index
#         return

#     # если уточнение не нужно — двигаемся дальше
#     s.q_index += 1
#     USER_STATES[m.from_user.id] = s
#     save_state()
#     await ask_next_question(m, s)


async def send_followup_quiz(m: Message, clarifications: dict):
    results = clarifications.get("results", [])
    if not results:
        return 0
    print(results)

    s = USER_STATES.get(m.from_user.id) or InterviewState()
    s.followup_polls = []
    s.followup_answers = []
    s.followup_meta = {}

    polls_sent = 0
    for i, res in enumerate(results, 1):
        if not res.get("valid", False):
            continue
        fup = res.get("followup")
        options = res.get("options", [])
        if not fup or not isinstance(options, list) or len(options) != 4:
            continue

        clean_options = []
        for opt in options:
            if not isinstance(opt, str):
                continue
            clean = opt.replace("\n", " ").strip()
            if len(clean) > 100:
                clean = clean[:97] + "..."
            clean_options.append(clean)
        if len(clean_options) != 4:
            continue

        idx = res.get("answer_index", 0)
        try:
            correct_idx = int(idx)
        except Exception:
            correct_idx = 0
        if correct_idx < 0 or correct_idx > 3:
            correct_idx = 0
        
        # рандомизируем позицию правильного ответа
        target_idx = random.randint(0, 3)
        if target_idx != correct_idx:
            clean_options[correct_idx], clean_options[target_idx] = clean_options[target_idx], clean_options[correct_idx]
            correct_idx = target_idx

        msg = await m.bot.send_poll(
            chat_id=m.chat.id,
            question=f"➕ Вопрос {i}: {fup}",
            options=clean_options,
            type=PollType.QUIZ,
            correct_option_id=correct_idx,
            is_anonymous=False
        )
        if msg and msg.poll:
            poll_id = msg.poll.id
            s.followup_polls.append(poll_id)
            s.followup_meta[poll_id] = {
                "followup": fup,
                "options": clean_options,
                "answer_index": correct_idx
            }
            polls_sent += 1

    USER_STATES[m.from_user.id] = s
    save_state()
    return polls_sent


async def finalize_and_report(m: Message, s: InterviewState):
    vac = VACANCIES[s.vacancy_key]

    # пары вопрос-ответ
    pairs = list(zip(vac.questions, s.answers))

    # шаг 1: уточнение (clarifier)
    clarif = await ClarifierService.clarify(pairs)

    # если будут квизы — сохраняем и ждём их завершения
    polls_sent = await send_followup_quiz(m, clarif)
    if polls_sent > 0:
        s = USER_STATES[m.from_user.id]
        setattr(s, "pending_clarification", clarif)
        USER_STATES[m.from_user.id] = s
        save_state()
        await m.answer_video_note(FSInputFile("media/frank/4_go_kviz_answers.mp4"))
        await asyncio.sleep(2)
        # await m.answer("Ответьте, пожалуйста, на квиз-вопросы выше. Как только вы закончите, я подготовлю итоговый отчёт.")
        return
    else:
        await m.answer_video_note(FSInputFile("media/frank/3_no_answers.mp4"))
        await asyncio.sleep(2)
        # await m.answer("Похоже для вас нет дополнительных вопросов.")

    # если квизов нет — сразу финализируем
    s = USER_STATES.get(m.from_user.id) or s
    setattr(s, "pending_clarification", clarif)
    USER_STATES[m.from_user.id] = s
    save_state()
    await finalize_after_followups(m.from_user.id, m.bot)

@router.poll_answer()
async def on_poll_answer(pa: PollAnswer, bot: Bot):
    uid = pa.user.id
    s = USER_STATES.get(uid)
    if not s or not s.followup_polls:
        return
    if pa.poll_id not in s.followup_polls:
        return

    meta = s.followup_meta.get(pa.poll_id, {})
    selected_idx = pa.option_ids[0] if pa.option_ids else -1
    correct_idx = int(meta.get("answer_index", 0))
    is_correct = (selected_idx == correct_idx)

    s.followup_answers.append({
        "poll_id": pa.poll_id,
        "followup": meta.get("followup"),
        "options": meta.get("options", []),
        "selected_index": selected_idx,
        "correct_index": correct_idx,
        "is_correct": is_correct,
    })
    USER_STATES[uid] = s
    save_state()

    answered_ids = {a["poll_id"] for a in s.followup_answers}
    if all(pid in answered_ids for pid in s.followup_polls):
        await finalize_after_followups(uid, bot)


async def finalize_after_followups(uid: int, bot: Bot):
    """
    Финальный этап после followup-вопросов:
    - собираем все ответы кандидата: свободные + квизы,
    - запускаем финальный анализ через AnalyzerService,
    - сохраняем JSON-отчёт,
    - отправляем результат пользователю.
    """
    s = USER_STATES.get(uid)
    if not s or not s.vacancy_key:
        return

    vac = VACANCIES[s.vacancy_key]

    free_answers = list(s.answers)
    quiz_answers = list(s.followup_answers or [])

    await bot.send_video_note(chat_id=uid, video_note=FSInputFile("media/frank/6_check_answers.mp4"))
    await asyncio.sleep(2)

    # # Запрашиваем обратную связь сразу после видео
    # try:
    #     await bot.send_video_note(chat_id=uid, video_note=FSInputFile("media/frank/5_pre_fin.mp4"))
    #     await asyncio.sleep(2)
    #     await bot.send_message(
    #         chat_id=uid,
    #         text="Пока я готовлю отчёт, пожалуйста, запишите голосовое сообщение с вашими впечатлениями об интервью. Что понравилось, что можно улучшить?"
    #     )
    #     s.feedback_requested = True
    #     USER_STATES[uid] = s
    #     save_state(uid)
    # except Exception as e:
    #     logging.exception(f"Ошибка запроса обратной связи: {e}")

    # # Запускаем анализ параллельно с ожиданием обратной связи
    eval_prompt = AnalyzerService.build_eval_prompt(vac, free_answers, quiz_answers)
    context = LLMService.build_context(s.history)
    raw = await LLMService.process_text(eval_prompt, context)

    try:
        start = raw.find("{")
        end = raw.rfind("}")
        cleaned = raw[start:end + 1]
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {"per_requirement": {}, "nice_to_have_hits": [], "overall": {}}

    match_percent = parsed.get("overall", {}).get("match_percent", 0)
    decision = parsed.get("overall", {}).get("decision", "hold")
    rationale = parsed.get("overall", {}).get("rationale", "")

    clarif = getattr(s, "pending_clarification", None)

    report = {
        "vacancy": vac.title,
        "free_answers": free_answers,
        "quiz_answers": quiz_answers,
        "analysis": parsed,
        "clarification": clarif,
        "computed_match_percent": match_percent,
        "decision": decision,
        "rationale": rationale,
    }

    os.makedirs("reports", exist_ok=True)
    path = f"reports/report_{uid}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Отправляем видео "результаты готовы" перед текстовым отчётом
    try:
        await bot.send_video_note(chat_id=uid, video_note=FSInputFile("media/frank/7_results.mp4"))
        await asyncio.sleep(2)
    except Exception as e:
        logging.exception(f"Ошибка отправки видео результатов: {e}")

    emoji = {"go": "✅", "hold": "🟨", "reject": "❌"}.get(decision, "ℹ️")

    strengths = parsed.get("strengths") or []
    weaknesses = parsed.get("weaknesses") or []
    quiz_summary = parsed.get("quiz_summary") or {}
    quiz_acc = quiz_summary.get("accuracy")
    rationale_short = (rationale or "").strip()
    if len(rationale_short) > 400:
        rationale_short = rationale_short[:397] + "..."

    lines = [
        f"<b>Результат:</b> {vac.title}",
        f"Соответствие: {match_percent}%",
        f"Рекомендация: {emoji} {decision}",
        f"Сильные стороны: {', '.join(strengths[:3]) if strengths else '—'}",
        f"Зоны роста: {', '.join(weaknesses[:3]) if weaknesses else '—'}"
    ]
    if isinstance(quiz_acc, (int, float)):
        try:
            qa_pct = int(round(float(quiz_acc) * 100))
            lines.append(f"Точность квиза: {qa_pct}%")
        except Exception:
            pass
    if rationale_short:
        lines.append(f"Обоснование: {rationale_short}")

    await bot.send_message(
        chat_id=uid,
        text="\n".join(lines),
        reply_markup=report_keyboard(uid).as_markup()
    )

    # Отправляем прощальное видео в самом конце
    try:
        await bot.send_video_note(chat_id=uid, video_note=FSInputFile("media/frank/8_baybay.mp4"))
    except Exception as e:
        logging.exception(f"Ошибка отправки прощального видео: {e}")

    # очистим временные поля
    s.followup_polls = []
    s.followup_answers = []
    s.followup_meta = {}
    if hasattr(s, "pending_clarification"):
        delattr(s, "pending_clarification")
    USER_STATES[uid] = s
    save_state()
