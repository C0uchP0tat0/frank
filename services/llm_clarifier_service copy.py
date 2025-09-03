import json
import asyncio
from gradio_client import Client


# class ClarifierService:
#     PROMPT = (
#         "Ты — HR-ИИ интервьюер.\n"
#         "У тебя есть список пар 'вопрос-ответ'.\n"
#         "Для каждого ответа оцени:\n"
#         " - соответствует ли ответ вопросу (true/false)\n"
#         " - если ответ неполный или невнятный, придумай короткий уточняющий вопрос (1 предложение).\n"
#         " - придумай 4 варианта ответов для уточняющего вопроса (строки).\n\n"
#         "Формат JSON:\n"
#         "{{\n"
#         "  \"results\": [\n"
#         "    {{\"q\": \"...\", \"a\": \"...\", \"valid\": true, \"followup\": \"...\", \"options\": [\"...\", \"...\"]}}\n"
#         "  ]\n"
#         "}}\n\n"
#         "Вот список пар:\n{pairs}"
#     )
class ClarifierService:
    PROMPT = (
        "Ты — HR-ИИ интервьюер для технических собеседований.\n"
        "У тебя есть список пар 'вопрос-ответ'.\n"
        "Твоя задача:\n"
        " - проверить, соответствует ли ответ кандидата исходному вопросу (valid: true/false).\n"
        " - если valid=false, НЕ генерируй дополнительный вопрос.\n"
        " - если valid=true, придумай небольшое практическое задание или вопрос, связанный с опытом, который кандидат описал в ответе.\n"
        " - для каждого такого задания сгенерируй ровно 4 варианта ответа (строки).\n"
        " - один из вариантов должен быть правильным, остальные правдоподобные, но неверные.\n"
        " - правильный вариант указывай через поле answer_index (значение от 0 до 3).\n"
        " - правильный вариант ДОЛЖЕН находиться на РАЗНЫХ позиции, а не только на первой или нулевой, что бы было сложнее угодать ответ.\n"
        " - каждый вариант ответа ДОЛЖЕН быть коротким (не более 100 символов).\n"
        " - варианты должны быть осмысленными и различаться между собой.\n"
        " - не придумывай ничего лишнего, оставляй задания строго по теме опыта кандидата.\n\n"
        "Формат JSON:\n"
        "{{\n"
        "  \"results\": [\n"
        "    {{\n"
        "       \"q\": \"<исходный вопрос>\",\n"
        "       \"a\": \"<ответ кандидата>\",\n"
        "       \"valid\": true|false,\n"
        "       \"followup\": \"<практическое задание или вопрос>\",\n"
        "       \"options\": [\"вариант1\", \"вариант2\", \"вариант3\", \"вариант4\"],\n"
        "       \"answer_index\": <индекс число от 0 до 3>\n"
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Вот список пар:\n{pairs}"
    )
    
    INLINE_PROMPT = (
        "Ты — тех. интервьюер. Тебе дана пара вопрос-ответ.\n"
        "Нужно решить: достаточно ли ответа. Если ответ бессмысленный или не относится к вопросу — followup не нужен.\n"
        "Если ответ по теме, но неполный — предложи ОДИН короткий уточняющий вопрос, который поможет раскрыть опыт.\n\n"
        "Формат JSON:\n"
        "{{\n"
        "  \"need_followup\": true|false,\n"
        "  \"reason\": \"кратко почему\",\n"
        "  \"followup_open\": \"короткий уточняющий вопрос\"  \n"
        "}}\n\n"
        "Вопрос: {q}\n"
        "Ответ: {a}\n"
    )

    @staticmethod
    async def clarify(pairs: list[tuple[str, str]]) -> dict:
        formatted_pairs = "\n".join([f"- Вопрос: {q}\n  Ответ: {a}" for q, a in pairs])
        prompt = ClarifierService.PROMPT.format(pairs=formatted_pairs)

        loop = asyncio.get_event_loop()
        retries = 9
        timeout_seconds = 120
        executor = None

        for attempt in range(retries):
            try:
                client = Client("Qwen/Qwen3-Demo")
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        executor,
                        lambda: client.predict(
                            input_value=prompt,
                            settings_form_value={
                                "model": "qwen3-235b-a22b",
                                "sys_prompt": "Ты HR-ИИ проверяющий качество ответов.",
                                "thinking_budget": 28,
                            },
                            api_name="/add_message",
                        ),
                    ),
                    timeout=timeout_seconds,
                )

                text = result[1]["value"][1]["content"][-1]["content"]
                start, end = text.find("{"), text.rfind("}")
                return json.loads(text[start:end+1])

            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    return {"results": [], "error": str(e)}
    
    @staticmethod
    async def clarify_single(q: str, a: str) -> dict:
        prompt = ClarifierService.INLINE_PROMPT.format(q=q, a=a)
        loop = asyncio.get_event_loop()
        retries = 3
        timeout_seconds = 60
        executor = None

        for attempt in range(retries):
            try:
                client = Client("Qwen/Qwen3-Demo")
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        executor,
                        lambda: client.predict(
                            input_value=prompt,
                            settings_form_value={
                                "model": "qwen3-235b-a22b",
                                "sys_prompt": "Ты HR-ИИ проверяющий полноту ответа.",
                                "thinking_budget": 18,
                            },
                            api_name="/add_message",
                        ),
                    ),
                    timeout=timeout_seconds,
                )
                text = result[1]["value"][1]["content"][-1]["content"]
                start, end = text.find("{"), text.rfind("}")
                return json.loads(text[start:end+1])
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    return {"need_followup": False, "error": str(e)}
