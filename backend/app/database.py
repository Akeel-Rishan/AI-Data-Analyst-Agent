"""Asynchronous SQLAlchemy database infrastructure."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base shared by all database models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session and close it after the request completes."""
    async with AsyncSessionLocal() as session:
        yield session


async def create_all_tables() -> None:
    """Create any missing database tables for development convenience."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


# Import the package only after Base exists so every model registers its table.
# Avoid requesting class attributes here: app.models may be partially initialized
# when a caller imports the model package before importing this module.
from app import models as _models  # noqa: E402, F401
