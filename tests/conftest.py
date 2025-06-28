import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.models_db import Base
from app.db.database import get_db

# Загружаем переменные окружения из .env.test
load_dotenv(dotenv_path=".env.test")

# Получаем строку подключения к тестовой базе
TEST_DATABASE_URL = os.getenv("DATABASE_URL")

# Создаём движок и фабрику сессий для тестовой базы
engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Перед всеми тестами: создаём таблицы, после — удаляем
@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Подмена зависимости FastAPI get_db на тестовую сессию
@pytest_asyncio.fixture(autouse=True)
def override_get_db():
    async def _override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = _override_get_db

# Асинхронный тестовый клиент с ASGITransport (правильно для httpx>=0.27)
@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
