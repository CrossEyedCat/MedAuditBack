"""
Middleware для сбора метрик Prometheus.
"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.metrics import (
    http_requests_total,
    http_request_duration_seconds,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware для сбора HTTP метрик."""

    async def dispatch(self, request: Request, call_next):
        """Сбор метрик для каждого запроса."""
        start_time = time.time()
        
        # Исключаем метрики из метрик
        if request.url.path == "/metrics":
            return await call_next(request)
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        # Нормализуем путь для метрик (убираем ID)
        endpoint = request.url.path
        # Заменяем UUID и числа на плейсхолдеры
        parts = endpoint.split("/")
        normalized_parts = []
        for part in parts:
            if part and (part.isdigit() or len(part) == 36):  # UUID или число
                normalized_parts.append("{id}")
            else:
                normalized_parts.append(part)
        normalized_endpoint = "/".join(normalized_parts)
        
        # Записываем метрики
        http_requests_total.labels(
            method=request.method,
            endpoint=normalized_endpoint,
            status_code=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=normalized_endpoint
        ).observe(duration)
        
        return response





