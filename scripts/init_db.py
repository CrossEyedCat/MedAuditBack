"""
Скрипт для инициализации базы данных.
Используется для создания начальных таблиц без миграций (для разработки).
"""
import asyncio
from app.core.database import init_db, engine
from app.models import *  # noqa: F401, F403


async def main():
    """Инициализация БД."""
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())


