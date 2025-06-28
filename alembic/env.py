import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool, create_engine
from alembic import context

# Загрузка переменных окружения из .env (если нужно)
from dotenv import load_dotenv
load_dotenv()

# Добавить app в PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем Base и ВСЕ МОДЕЛИ!
from app.db.models_db import Base, Room, Player  # <-- импортируй ВСЕ модели!

# Alembic Config object
config = context.config

# Логирование через файл конфигурации
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем метаданные
target_metadata = Base.metadata

def get_url():
    """
    Возвращает синхронный SQLAlchemy URL для Alembic.
    Если в .env указано postgresql+asyncpg — меняем на postgresql.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("No DATABASE_URL provided for alembic!")
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
