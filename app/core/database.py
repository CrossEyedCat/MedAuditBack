"""
Настройка подключения к базе данных.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Создание асинхронного движка БД
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,  # Переиспользование соединений каждый час
    pool_reset_on_return="commit",  # Сброс транзакций при возврате в пул
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Базовый класс для моделей
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency для получения сессии БД.
    Используется в FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Инициализация БД (создание таблиц)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Закрытие соединений с БД."""
    await engine.dispose()

