FROM python:3.11-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
