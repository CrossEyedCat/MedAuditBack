"""
Настройка подключения к Redis.
"""
import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

# Глобальный объект Redis
redis_client: Redis | None = None


async def init_redis() -> Redis:
    """Инициализация подключения к Redis."""
    global redis_client
    redis_client = await redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    return redis_client


async def get_redis() -> Redis:
    """Получить клиент Redis."""
    if redis_client is None:
        return await init_redis()
    return redis_client


async def close_redis() -> None:
    """Закрыть подключение к Redis."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


