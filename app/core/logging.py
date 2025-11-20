"""
Настройка логирования.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def setup_logging() -> None:
    """Настройка структурированного логирования."""
    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Настройка стандартного логирования
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )


def get_logger(name: str) -> Any:
    """Получить логгер с указанным именем."""
    return structlog.get_logger(name)


