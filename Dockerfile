FROM python:3.11-slim

WORKDIR /code

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения и миграции
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Копируем тесты и переменные окружения для тестов (если нужны)
COPY ./tests ./tests
COPY .env .env
COPY .env.test .env.test

# Команда по умолчанию — применяем миграции и запускаем сервер
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
