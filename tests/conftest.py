import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

from app.main import app
from app.db.database import get_db
from app.db.models_db import Base

# Загружаем переменные окружения для тестовой БД
load_dotenv(".env.test")
DATABASE_URL = os.getenv("DATABASE_URL")

@pytest_asyncio.fixture
async def db_engine():
    """
    Создает отдельный async engine для каждого теста.
    """
    engine = create_async_engine(DATABASE_URL, future=True)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def prepare_database(db_engine):
    """
    Сбрасывает и создает все таблицы перед каждым тестом.
    """
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest_asyncio.fixture
async def session_maker(db_engine, prepare_database):
    """
    Фикстура для создания sessionmaker, привязанного к engine.
    """
    return sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture
async def override_get_db(session_maker):
    """
    Подменяет зависимость get_db на тестовую сессию.
    """
    async def _get_db():
        async with session_maker() as session:
            yield session
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()  # Очищаем подмену после теста

@pytest_asyncio.fixture
async def async_client(override_get_db):
    """
    Тестовый AsyncClient для взаимодействия с FastAPI-приложением.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
