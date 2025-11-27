"""
Middleware для rate limiting.
"""
import time
from typing import Dict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.redis import get_redis
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения частоты запросов."""

    def __init__(self, app, calls: int = 100, period: int = 60):
        """
        Инициализация rate limiter.

        Args:
            app: ASGI приложение
            calls: Количество разрешенных запросов
            period: Период времени в секундах
        """
        super().__init__(app)
        self.calls = calls
        self.period = period

    async def dispatch(self, request: Request, call_next):
        """Проверка rate limit перед обработкой запроса."""
        # Получаем IP адрес клиента
        client_ip = request.client.host if request.client else "unknown"

        # Получаем путь для определения типа endpoint
        path = request.url.path

        # Определяем лимиты в зависимости от endpoint
        if path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register"):
            # Более строгие лимиты для аутентификации
            calls = 5
            period = 60
        elif path.startswith("/api/v1/documents/upload"):
            # Лимиты для загрузки файлов
            calls = 10
            period = 60
        elif path.startswith("/api/v1/reports/generate"):
            # Лимиты для генерации отчетов
            calls = 5
            period = 60
        else:
            # Стандартные лимиты
            calls = self.calls
            period = self.period

        # Проверяем rate limit
        try:
            redis = await get_redis()
            key = f"rate_limit:{client_ip}:{path}"
            current = await redis.get(key)

            if current and int(current) >= calls:
                logger.warning(
                    "Rate limit exceeded",
                    client_ip=client_ip,
                    path=path,
                    calls=calls,
                    period=period,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Превышен лимит запросов. Максимум {calls} запросов за {period} секунд.",
                    headers={"Retry-After": str(period)},
                )

            # Увеличиваем счетчик
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, period)
            await pipe.execute()

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error checking rate limit", error=str(e))
            # В случае ошибки Redis продолжаем выполнение

        response = await call_next(request)
        return response





