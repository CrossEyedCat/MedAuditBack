"""
Сервис для кеширования данных.
"""
from typing import Optional, Any
from datetime import timedelta

from app.core.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Сервис для работы с кешем."""

    @staticmethod
    async def get(key: str) -> Optional[Any]:
        """
        Получение значения из кеша.

        Args:
            key: Ключ кеша

        Returns:
            Значение или None
        """
        try:
            redis = await get_redis()
            value = await redis.get(key)
            if value:
                import json
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("Error getting from cache", key=key, error=str(e))
            return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Сохранение значения в кеш.

        Args:
            key: Ключ кеша
            value: Значение для сохранения
            ttl: Время жизни в секундах

        Returns:
            True если успешно сохранено
        """
        try:
            redis = await get_redis()
            import json
            serialized = json.dumps(value)
            await redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning("Error setting cache", key=key, error=str(e))
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """
        Удаление значения из кеша.

        Args:
            key: Ключ кеша

        Returns:
            True если успешно удалено
        """
        try:
            redis = await get_redis()
            await redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Error deleting from cache", key=key, error=str(e))
            return False

    @staticmethod
    async def delete_pattern(pattern: str) -> int:
        """
        Удаление всех ключей по паттерну.

        Args:
            pattern: Паттерн для поиска ключей

        Returns:
            Количество удаленных ключей
        """
        try:
            redis = await get_redis()
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.warning("Error deleting pattern from cache", pattern=pattern, error=str(e))
            return 0


