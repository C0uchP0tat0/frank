from gradio_client import Client, handle_file
import asyncio


class TTSService:
    @staticmethod
    async def process_text(text: str, retries: int = 9, delay: float = 2.0) -> str:
        """
        Обработка аудио файла и распознавание речи с ретраями.
        :param file_path: путь к аудио
        :param retries: кол-во попыток
        :param delay: задержка между попытками
        """
        loop = asyncio.get_event_loop()
        backoff = 2.0
        current_delay = 2.0
        

        for attempt in range(1, retries + 1):
            try:
                client = Client("Qwen/Qwen-TTS-Demo")
                result = await loop.run_in_executor(
                    None,
                    lambda: client.predict(
                        text=text,
                        voice="Sunny",
                        # voice="Dylan",
                        api_name="/predict"
                    ),
                )
                return str(result)

            except Exception as e:
                if attempt < retries:
                    await asyncio.sleep(delay)
                    current_delay *= backoff
                else:
                    return f"Ошибка генерации голоса после {retries} попыток: {e}"


# Вызов функции
async def main():
    result = await TTSService.process_text("ну Ё моё ну ты чё а блин")
    print(result)

# Запуск
if __name__ == "__main__":
    asyncio.run(main())