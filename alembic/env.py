from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import os
import sys

# Добавляем путь к app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.models_db import Base  # <-- Импортируем Base для metadata

# Alembic Config
config = context.config

# Logging config
fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
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
    from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        async with context.begin_transaction():
            await context.run_migrations()

    import asyncio
    asyncio.run(run_async_migrations(connectable, do_run_migrations))

async def run_async_migrations(connectable, do_run_migrations):
    async with connectable.connect() as connection:
        await do_run_migrations(connection)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
