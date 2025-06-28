import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.models_db import Base

# 1. Берём строку подключения из переменных окружения
TEST_DATABASE_URL = os.getenv("DATABASE_URL")  # должен быть настроен на отдельную тестовую базу!

# 2. Создаём асинхронный engine и сессию для тестов
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
AsyncSessionTest = sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    # 3. Перед запуском тестов — создаём все таблицы
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 4. После тестов — можно очистить БД (по желанию)
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture()
async def test_db_session():
    # 5. Используем отдельную сессию для каждого теста
    async with AsyncSessionTest() as session:
        yield session
