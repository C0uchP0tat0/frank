import os
import random
from gradio_client import Client, handle_file
import asyncio

from services.proxy import PROXY_LIST


class AudioService:
    @staticmethod
    async def process_audio_file(file_path: str, retries: int = 9, delay: float = 2.0, timeout: float = 120.0, backoff = 2.0) -> str:
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

                # client = Client("hf-audio/whisper-large-v3")
                client = Client("hf-audio/whisper-large-v3-turbo")

                # оборачиваем вызов в таймаут
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.predict(
                            inputs=handle_file(file_path),
                            task="transcribe",
                            api_name="/predict"
                        ),
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
    result = await AudioService.process_audio_file("/home/lecoo/haks/MORE_Tech_VTB_17_08-20_09_25/services/output.wav")
    print(result)

# Запуск
if __name__ == "__main__":
    asyncio.run(main())