"""
Главный файл приложения MediAudit.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.redis import init_redis, close_redis
from app.core.exceptions import (
    APIException,
    api_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.api.v1.router import api_router
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.query_logger import QueryLoggerMiddleware
from app.middleware.metrics import MetricsMiddleware
from app.utils.metrics import get_metrics_response
from fastapi.exceptions import RequestValidationError

# Настройка логирования
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hooks для инициализации и закрытия ресурсов."""
    # Startup
    logger.info("Starting MediAudit API...")
    await init_redis()
    logger.info("Redis initialized")
    logger.info("MediAudit API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MediAudit API...")
    await close_redis()
    logger.info("MediAudit API shut down successfully")


# Создание приложения FastAPI
app = FastAPI(
    title="MediAudit API",
    description="Система для автоматического аудита медицинской документации с использованием NLP",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Безопасные HTTP заголовки
app.add_middleware(SecurityHeadersMiddleware)

# Логирование медленных запросов
app.add_middleware(QueryLoggerMiddleware)

# Метрики Prometheus
app.add_middleware(MetricsMiddleware)

# Rate limiting (только для production, в dev можно отключить)
if not settings.DEBUG:
    app.add_middleware(RateLimitMiddleware)

# Обработчики исключений
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Корневой endpoint для проверки работы API."""
    return {
        "message": "MediAudit API",
        "version": "1.0.0",
        "docs": "/api/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_response()

