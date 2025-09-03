import os
import random
from gradio_client import Client, handle_file
import asyncio
from services.proxy import PROXY_LIST
# from proxy import PROXY_LIST


class VoiceCloneService:
    @staticmethod
    async def process_text(text: str, retries: int = 6, delay: float = 2.0, timeout: float = 300.0, backoff = 2.0) -> str:
        """
        Обработка аудио файла и распознавание речи с ретраями и таймаутом.
        :param file_path: путь к аудио
        :param retries: кол-во попыток
        :param delay: задержка между попытками
        :param timeout: таймаут (секунд) на один запрос
        """
        loop = asyncio.get_event_loop()
        current_delay = delay

        for attempt in range(1, retries + 1):
            try:
                if len(PROXY_LIST) > 0:
                    proxy = random.choice(PROXY_LIST)
                    print(f"[Попытка {attempt}] Используем прокси: {proxy}")
                    os.environ["HTTP_PROXY"] = proxy
                    os.environ["HTTPS_PROXY"] = proxy


                # client = Client("tonyassi/voice-clone")
                client = Client("englissi/Voice-Clone-Multilingual")
                # client = Client("https://kikirilkov-voice-cloning.hf.space/--replicas/rcjt8/")

                # оборачиваем вызов в таймаут
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.predict(
                            text=text,
                            # audio=handle_file("services/gde-nashi-dengi.mp3"),
                            # speaker_wav=handle_file("services/film-smotryu--rasska-syujeta-.mp3"),
                            speaker_wav=handle_file("services/MVOICE.mp3"),
                            language="ru",
                            api_name="/predict"
                        ),
                        # lambda: client.predict(
                        #     text,
                        #     # handle_file("services/film-smotryu--rasska-syujeta-.mp3"),
                        #     handle_file("services/MVOICE.mp3"),
                        #     # handle_file("services/WVOICE.mp3"),
                        #     "ru",
                        #     api_name="/predict"
                        # ),
                    ),
                    timeout=timeout
                )
                return str(result)

            except asyncio.TimeoutError:
                print(f"⏳ Таймаут ({timeout}с) на попытке {attempt}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                    current_delay *= backoff
                else:
                    return f"Ошибка: превышен таймаут {timeout} секунд после {retries} попыток"
            except Exception as e:
                print(f"⚠️ Ошибка: {e}")
                if attempt < retries:
                    await asyncio.sleep(delay)
                else:
                    return f"Ошибка распознавания после {retries} попыток: {e}"

# Вызов функции
async def main():
    # questions = [
    #     "Коротко расскажите о вашем релевантном опыте в Python?",
    #     "Какой опыт у вас с веб-фреймворками Фаст АПИ, Айо эйч ти ти пи, Джанго?",
    #     "Опишите опыт работы с базами данных и оптимизацией запросов.",
    #     "Как вы тестируете код? Какие инструменты и подходы используете?",
    #     "Опишите опыт контейнеризации и деплоя Докер, Ка8Эс, Си ай си ди."
    # ]
    
    questions = [
        # "Расскажите о проекте машинного обучения (Эм-Эл), которым вы гордитесь.",
        # "Как вы выбираете и проверяете модели на качество (валидация)?",
        # "Опишите ваш опыт развёртывания моделей в продакшн и их мониторинга.",
        # "Как вы работаете с данными (очистка и подготовка признаков — фичеринг)?",
        # "Опыт работы с Эс-Кью-Эль и визуализацией данных: используемые инструменты и подходы."
    ]
    
    # questions = [
    #     "Опишите опыт подготовки бизнес-требований и постановки задач.",
    #     "Приходилось ли вам работать с антифрод-системами или ПОД/ФТ-системами (Противодействие Отмыванию Денег / Финансовый Транзакционный контроль)?",
    #     "Как вы взаимодействовали с разработчиками при постановке задач?",
    #     "Как вы тестируете реализованные требования?",
    #     "Опишите опыт работы с банковскими процессами (карты, Дистанционное банковское обслуживание и так далее)."
    # ]

    # questions = [
    #     "Опишите ваш опыт работы с серверным оборудованием искс 86",
    #     "Есть ли у вас опыт диагностики и устранения инцидентов?",
    #     "Работали ли вы с системами Configuration Management Database — база управления конфигурациями и Data Center Infrastructure Management — управление инфраструктурой ЦОД?",
    #     "Как вы документируете выполненные работы?",
    #     "Был ли у вас опыт работы с подрядчиками и обслуживанием Центра обработки данных?"
    # ]
    
    questions = [
        # """Приветствую Вас, меня зовут Фрэнк и я цифровой ЭйчАр ЭйАй Аватар,
        # Приглашаю вас на небольшое интервью со мной,
        # Оно займет не более двадцати минут вашего времени,
        # Это необходимо для того, чтобы мы убедились в соответствии вашего опыта нашей вакансии,
        # Далее вам предстоит ответить на ряд вопросов""",
        # "Спасибо! Опираясь на Ваши ответы подготовлю дополнительные вопросы, вернусь к Вам через минуту",
        # "Оказалось, что для принятия решения по Вашей кандидатуре, дополнительных вопросов не возникло",
        # "Ответьте, пожалуйста, на квиз-вопросы выше.",
        # """Перед тем как я сформирую финальный отчет и отправлю его в ЭйчАр отдел и дам Вам обратную связь по интервью,
        # прошу рассказать о ваших зарплатных ожиданиях и пожеланиях к работодателю, а так же  поделиться своими впечатлениями о нашем общение""",
        # "Ваши ответы приняты, мне потребуется немного времени что бы их проанализировать и вернуться к Вам с обратной связью",
        # "Прошу Вас ознакомиться с результатами прохождения интервью",
        # "Наше общение подошло к концу Cпасибо за прохождение интервью, мне было приятно с вами пообщаться, С уважением Ваш цифровой ЭйчАр ЭйАй Аватар Фрэнк"
    ]


    async def process_and_print(idx, q):
        result = await VoiceCloneService.process_text(q)
        print(idx, q, "-------", result)

    tasks = [process_and_print(i + 1, q) for i, q in enumerate(questions)]
    await asyncio.gather(*tasks)
    
    

# Запуск
if __name__ == "__main__":
    asyncio.run(main())