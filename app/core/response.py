"""
Стандартизированные форматы ответов API.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """Стандартизированный формат успешного ответа."""

    success: bool = True
    data: Any
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Стандартизированный формат ответа с ошибкой."""

    success: bool = False
    error: Dict[str, Any]
    message: Optional[str] = None


def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Создание стандартизированного успешного ответа.

    Args:
        data: Данные ответа
        message: Опциональное сообщение

    Returns:
        Словарь с форматированным ответом
    """
    return {
        "success": True,
        "data": data,
        "message": message,
    }


def error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Создание стандартизированного ответа с ошибкой.

    Args:
        code: Код ошибки
        message: Сообщение об ошибке
        details: Дополнительные детали

    Returns:
        Словарь с форматированным ответом
    """
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


