import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_database_url():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set! This project only runs in Docker with Postgres.")
    return db_url

def get_engine():
    return create_async_engine(get_database_url(), echo=True, future=True)

def get_session_maker():
    engine = get_engine()
    return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session
