"""
Middleware для логирования медленных запросов к БД.
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)

# Порог для медленных запросов (в секундах)
SLOW_QUERY_THRESHOLD = 1.0


class QueryLoggerMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования медленных запросов."""

    async def dispatch(self, request: Request, call_next):
        """Логирование времени выполнения запросов."""
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Логируем медленные запросы
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(
                "Slow request detected",
                path=request.url.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code,
                client_ip=request.client.host if request.client else "unknown",
            )
        else:
            logger.debug(
                "Request processed",
                path=request.url.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code,
            )
        
        # Добавляем заголовок с временем выполнения
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
        return response

