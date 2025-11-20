"""
Конфигурация для pytest.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.redis import get_redis
from app.models.user import User
from app.utils.password import get_password_hash


# Тестовая БД (in-memory SQLite для тестов)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    """Переопределение зависимости get_db для тестов."""
    async with TestSessionLocal() as session:
        yield session


async def override_get_redis():
    """Mock Redis для тестов."""
    # В реальных тестах можно использовать fakeredis
    class MockRedis:
        def __init__(self):
            self.data = {}

        async def get(self, key: str):
            return self.data.get(key)

        async def setex(self, key: str, time: int, value: str):
            self.data[key] = value

        async def delete(self, key: str):
            self.data.pop(key, None)

    return MockRedis()


@pytest.fixture(scope="function")
async def db_session():
    """Создание тестовой сессии БД."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Создание тестового клиента."""
    async def override_get_db_dep():
        async for session in override_get_db():
            yield session

    app.dependency_overrides[get_db] = override_get_db_dep
    app.dependency_overrides[get_redis] = override_get_redis

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Создание тестового пользователя."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

