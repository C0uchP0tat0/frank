import json
import asyncio
from typing import Dict, List
from gradio_client import Client
from vacancies import Vacancy

PROMPT = (
    "Ты — опытный тех. рекрутер. Твоя задача — глубоко проанализировать резюме и сопоставить его с вакансией.\n\n"
    "ВАЖНО: Анализируй опыт работы ДЕТАЛЬНО. Ищи скрытые связи и косвенные соответствия требованиям.\n\n"
    "Вакансия:\n"
    "Название: {title}\n"
    "Требования (must):\n{reqs}\n"
    "Плюсы (nice):\n{nice}\n\n"
    "Резюме:\n"
    "Заголовок: {cv_title}\n"
    "Опыт: {cv_exp}\n"
    "Навыки: {cv_skills}\n\n"
    "ИНСТРУКЦИИ ПО АНАЛИЗУ:\n"
    "1. Внимательно изучи весь опыт работы кандидата\n"
    "2. Ищи КОСВЕННЫЕ соответствия требованиям (например, если требуется Python, а у кандидата есть опыт автоматизации - это может быть связано)\n"
    "3. Оценивай глубину опыта, а не только прямые совпадения\n"
    "4. Учитывай смежные технологии и навыки\n"
    "5. Если опыт работы большой и разнообразный - это плюс\n"
    "6. Ищи признаки способности к обучению и адаптации\n\n"
    "Верни ТОЛЬКО JSON:\n"
    "{{\n"
    "  \"fit\": true|false,\n"
    "  \"match_percent\": 0..100,\n"
    "  \"rationale\": \"подробное обоснование с указанием найденных соответствий\",\n"
    "  \"strengths\": [\"конкретные сильные стороны из опыта\"],\n"
    "  \"gaps\": [\"пробелы в навыках\"],\n"
    "  \"decision\": \"go\"|\"hold\"|\"reject\",\n"
    "  \"experience_analysis\": \"детальный анализ опыта работы\",\n"
    "  \"hidden_matches\": [\"скрытые соответствия требованиям\"]\n"
    "}}"
)

async def classify_one(vac: Vacancy, cv: Dict[str, str]) -> Dict:
    prompt = PROMPT.format(
        title=vac.title,
        reqs="\n".join(f"- {r}" for r in vac.requirements),
        nice="\n".join(f"- {r}" for r in vac.nice_to_have),
        cv_title=cv.get("title",""),
        cv_exp=cv.get("experience",""),
        cv_skills=cv.get("skills",""),
    )
    loop = asyncio.get_event_loop()
    for attempt in range(6):
        try:
            client = Client("Qwen/Qwen2.5-Coder-demo")
            result = await loop.run_in_executor(
                None,
                lambda: client.predict(
                    query=prompt,
                    history=[],
                    system="Ты HR-ИИ с глубоким пониманием IT-сферы. Анализируй опыт работы детально и ищи скрытые соответствия. Верни только корректный JSON.",
                    radio="32B",
                    api_name="/model_chat"
                )
            )
            text = result[1][0][1]
            start, end = text.find("{"), text.rfind("}")
            return json.loads(text[start:end+1])
        except Exception:
            if attempt == 6:
                return {"fit": False, "decision": "hold", "rationale": "parse_error"}
            await asyncio.sleep(0.5)

async def classify_bulk(vac: Vacancy, cvs: List[Dict[str, str]]) -> List[Dict]:
    results = await asyncio.gather(*[classify_one(vac, cv) for cv in cvs])
    return results