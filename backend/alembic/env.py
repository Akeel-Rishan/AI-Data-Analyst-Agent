"""Alembic environment configured for the application's async database."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.database import Base
from app.models import AnalysisResult, Conversation, Dataset, Message, User


config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# These imports intentionally ensure every table is present in Base.metadata.
REGISTERED_MODELS = (User, Dataset, Conversation, Message, AnalysisResult)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run Alembic's synchronous migration operations on a connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and adapt its connection for Alembic."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_async_compat() -> None:
    """Run the async migration coroutine from Alembic's sync entry point."""
    asyncio.run(run_async_migrations())


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    run_async_compat()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
