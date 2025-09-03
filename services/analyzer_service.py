from typing import List, Dict, Any
from vacancies import Vacancy
import json

class AnalyzerService:
    @staticmethod
    def build_eval_prompt(vac: Vacancy, free_answers: List[str], quiz_answers: List[Dict[str, Any]]) -> str:
        req_str = "\n".join(f"- {r}" for r in vac.requirements)
        nice_str = "\n".join(f"- {r}" for r in vac.nice_to_have)
        weights_json = json.dumps(vac.weights, ensure_ascii=False)

        # Добавляем вопросы, которые были заданы кандидату
        questions_str = "\n".join(f"Вопрос {i+1}: {q}" for i, q in enumerate(vac.questions))

        fa_str = "\n\n".join(f"Свободный ответ {i+1}: {a}" for i, a in enumerate(free_answers))

        # Структурируем квизы: один блок на квиз
        qa_blocks = []
        for i, qa in enumerate(quiz_answers):
            followup = qa.get("followup", "")
            options = qa.get("options", [])
            sel = qa.get("selected_index", -1)
            cor = qa.get("correct_index", -1)
            is_ok = qa.get("is_correct", False)
            opts_str = "\n".join([f"  {j}. {opt}" for j, opt in enumerate(options)])
            qa_blocks.append(
                f"Квиз {i+1}:\n"
                f"Вопрос: {followup}\n"
                f"Варианты:\n{opts_str}\n"
                f"Выбор кандидата: {sel}\n"
                f"Правильный ответ: {cor}\n"
                f"Правильно: {is_ok}"
            )
        qa_str = "\n\n".join(qa_blocks) if qa_blocks else "—"

        return (
            "Ты выступаешь в роли ведущего технического интервьюера. "
            "Проанализируй ответы кандидата относительно требований вакансии, "
            "используя и свободные ответы, и результаты квизов. "
            "Верни ТОЛЬКО валидный JSON без комментариев.\n\n"
            
            f"Требования (must):\n{req_str}\n\n"
            f"Плюсы (nice-to-have):\n{nice_str}\n\n"
            f"Вес каждого must-требования в долях (0..1), сумма ≈ 1: {weights_json}\n\n"

            f"Вопросы, заданные кандидату:\n{questions_str}\n\n"

            "Свободные ответы кандидата:\n"
            f"{fa_str or '—'}\n\n"

            "Ответы кандидата в квизах:\n"
            f"{qa_str}\n\n"

            "Оцени следующее:\n"
            " - Для каждого must-требования рассчитай score (0..1) и укажи evidence: "
            "краткую, проверяемую цитату/факт из свободных ответов и/или правильных квизов.\n"
            " - Отрази влияние неверных квизов: если кандидат ошибался по теме требования, "
            "уменьши score и отметь это в evidence.\n"
            " - Если ответы кандидата поверхностные, а квизов не было то такие ответы не засчитывай.\n"
            " - Определи, какие nice-to-have кандидат продемонстрировал (по любым источникам).\n"
            " - Оцени согласованность: не противоречат ли свободные ответы результатам квизов.\n"
            " - Учитывай soft skills (коммуникация, логичность, ясность, эмоциональная окраска). "
            "Если они явно слабые — снижай итоговые оценки и отрази это в evidence и rationale.\n"
            " - Выдели сильные стороны (strengths) и зоны роста (weaknesses) в виде списков.\n"
            " - Дай конкретные рекомендации (improvement_advice) по улучшению.\n"
            " - Сформируй общий вывод (overall): match_percent (0..100), decision ('go'|'hold'|'reject'), "
            "и развёрнутое rationale, опираясь на веса must-требований.\n\n"

            "Формат JSON:\n"
            "{\n"
            "  \"per_requirement\": {\n"
            "     \"<требование>\": {\n"
            "         \"score\": 0..1,\n"
            "         \"evidence\": \"краткое обоснование с отсылкой к ответу/квизу\",\n"
            "         \"depth\": 0..1,\n"
            "         \"completeness\": 0..1\n"
            "     },\n"
            "     ...\n"
            "  },\n"
            "  \"quiz_summary\": {\n"
            "     \"accuracy\": 0..1,\n"
            "     \"incorrect_items\": [\n"
            "        {\"question\": \"...\", \"selected_index\": 0, \"correct_index\": 2}\n"
            "     ]\n"
            "  },\n"
            "  \"nice_to_have_hits\": [\"<попавшие плюсы>\", ...],\n"
            "  \"consistency\": \"описание согласованности свободных ответов и квизов\",\n"
            "  \"strengths\": [\"...\"],\n"
            "  \"weaknesses\": [\"...\"],\n"
            "  \"improvement_advice\": [\"...\"],\n"
            "  \"overall\": {\n"
            "     \"match_percent\": 0..100,\n"
            "     \"decision\": \"go\" | \"hold\" | \"reject\",\n"
            "     \"rationale\": \"развёрнутое объяснение решения\"\n"
            "  }\n"
            "}"
        )
