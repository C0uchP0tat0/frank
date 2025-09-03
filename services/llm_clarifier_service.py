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
        "Ты — HR-ИИ, выступающий в роли интервьюера уровня middle/senior.\n"
        "У тебя есть список пар 'вопрос-ответ'.\n"
        "Твоя задача:\n"
        " - определить, относится ли ответ кандидата к исходному вопросу (valid: true/false).\n"
        " - если valid=false, НЕ предлагай followup и не строй квиз.\n"
        " - если valid=true:\n"
        "     * придумай уточняющий вопрос или мини-практическое задание с подвохом, "
        "       чтобы проверить реальную глубину опыта кандидата.\n"
        "     * вопрос должен быть не банальным, а связанным с практикой, типичными ошибками "
        "       или сложными ситуациями (как техническими, так и бизнесовыми).\n"
        "     * Вопросы должны быть абстрактными, а не ситуативными.\n"
        "     * сгенерируй ровно 4 варианта ответа.\n"
        "     * среди вариантов:\n"
        "         - один правильный;\n"
        "         - три правдоподобных, но неверных (типичные ошибки, мифы, упрощения).\n"
        "     * правильный вариант указывай через поле answer_index (0–3).\n"
        "     * каждый вариант должен быть коротким (<100 символов), но осмысленным.\n"
        "     * избегай школьных и тривиальных вопросов.\n"
        "     * варианты должны быть реально различимы по смыслу, а не просто перефразированы.\n"
        " - всегда учитывай контекст ответа кандидата, даже если он написан с ошибками или "
        "   неаккуратно (например, 'ICB диплома диплома' трактуй как CI/CD в дипломном проекте).\n\n"
        "Формат JSON:\n"
        "{{\n"
        "  \"results\": [\n"
        "    {{\n"
        "       \"q\": \"<исходный вопрос>\",\n"
        "       \"a\": \"<ответ кандидата>\",\n"
        "       \"valid\": true|false,\n"
        "       \"followup\": \"<уточняющий вопрос или практическое задание>\",\n"
        "       \"options\": [\"вариант1\", \"вариант2\", \"вариант3\", \"вариант4\"],\n"
        "       \"answer_index\": <число от 0 до 3>\n"
        "    }}\n"
        "  ]\n"
        "}}\n\n"
        "Вот список пар:\n{pairs}"
    )

    
    INLINE_PROMPT = (
        "Ты — интервьюер.\n"
        "Тебе дана пара вопрос-ответ.\n"
        "Нужно решить: достаточно ли ответа.\n"
        "- Если ответ бессмысленный или не по теме — followup не нужен.\n"
        "- Если ответ по теме, но слишком общий или поверхностный — предложи ОДИН уточняющий вопрос.\n"
        "- Уточняющий вопрос должен быть практическим или с подвохом (например, про тонкие места, "
        "подводные камни, типичные ошибки, реальные ситуации).\n"
        "- Никогда не задавай банальных вопросов «а расскажите подробнее».\n"
        "- Если ответ написан с ошибками или повторами, но смысл по теме — трактуй как по теме.\n\n"
        "Формат JSON:\n"
        "{{\n"
        "  \"need_followup\": true|false,\n"
        "  \"reason\": \"кратко почему\",\n"
        "  \"followup_open\": \"короткий уточняющий вопрос (с подвохом или проверкой практики)\"  \n"
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
                # client = Client("Qwen/Qwen2.5-Coder-demo")
                # result = await asyncio.wait_for(
                #     loop.run_in_executor(
                #         executor,
                #         lambda: client.predict(
                #             query=prompt,
                #             history=[],
                #             system="Ты HR-ИИ проверяющий качество ответов.",
                #             radio="32B",
                #             api_name="/model_chat"
                #         ),
                #     ),
                #     timeout=timeout_seconds,
                # )

                # text = result[1][0][1]
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
                print(text)
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
                client = Client("Qwen/Qwen2.5-Coder-demo")
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        executor,
                        lambda: client.predict(
                            query=prompt,
                            history=[],
                            system="Ты HR-ИИ проверяющий качество ответов.",
                            radio="32B",
                            api_name="/model_chat"
                        ),
                    ),
                    timeout=timeout_seconds,
                )

                text = result[1][0][1]
                print(text)
                start, end = text.find("{"), text.rfind("}")
                return json.loads(text[start:end+1])
            except Exception as e:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    return {"need_followup": False, "error": str(e)}
