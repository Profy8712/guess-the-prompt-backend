import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine  # Синхронный движок!
from alembic import context

# Для .env (например, DATABASE_URL)
from dotenv import load_dotenv
load_dotenv()

# Добавляем app в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем Base для metadata
from app.db.models_db import Base

# Alembic config
config = context.config

# Логирование
fileConfig(config.config_file_name)

# Метаданные моделей
target_metadata = Base.metadata

def get_url():
    # Берём DATABASE_URL из env и убираем asyncpg (только для миграций!)
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("No DATABASE_URL provided for alembic!")
    # Если ты работаешь с asyncpg — заменяем на sync для миграций
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql")
    return url

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
