"""
Middleware для безопасности.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления безопасных HTTP заголовков."""

    async def dispatch(self, request: Request, call_next):
        """Добавление безопасных заголовков к ответу."""
        response = await call_next(request)

        # Безопасные заголовки
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content-Security-Policy (базовая настройка)
        # В production нужно настроить более строгие правила
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


