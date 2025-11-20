"""
Кастомные исключения и обработчики ошибок.
"""
from typing import Optional, Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class APIException(Exception):
    """Базовое исключение для API ошибок."""

    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Инициализация исключения.

        Args:
            status_code: HTTP статус код
            message: Сообщение об ошибке
            error_code: Код ошибки
            details: Дополнительные детали
        """
        self.status_code = status_code
        self.message = message
        self.error_code = error_code or f"ERROR_{status_code}"
        self.details = details or {}


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Обработчик кастомных исключений API."""
    logger.error(
        "API exception",
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Обработчик ошибок валидации."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(
        "Validation error",
        path=request.url.path,
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Ошибка валидации данных",
                "details": {
                    "errors": errors,
                },
            }
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик общих исключений."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Внутренняя ошибка сервера",
                "details": {},
            }
        },
    )


