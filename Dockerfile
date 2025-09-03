# Используем Python 3.11 для стабильности
FROM python:3.12-slim

# # Устанавливаем системные зависимости
# RUN apt-get update && apt-get install -y \
#     ffmpeg \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY Pipfile Pipfile.lock ./

# Устанавливаем pipenv и зависимости
RUN pip install pipenv && \
    pipenv install --system --deploy

# Копируем исходный код
COPY . .

# Создаем необходимые директории
RUN mkdir -p downloads reports state media/questions media/frank

# Устанавливаем права на запись
RUN chmod -R 755 downloads reports state media

# Открываем порт (если понадобится для веб-интерфейса)
EXPOSE 8000

# Запускаем бота
CMD ["python", "main.py"]