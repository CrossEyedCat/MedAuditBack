"""
Конфигурация приложения.
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения."""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://medaudit:medaudit_password@localhost:5432/medaudit_db",
        description="URL подключения к PostgreSQL",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="URL подключения к Redis",
    )

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Секретный ключ для JWT",
    )
    ALGORITHM: str = Field(default="HS256", description="Алгоритм шифрования JWT")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Время жизни access token в минутах"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Время жизни refresh token в днях"
    )

    # Application
    DEBUG: bool = Field(default=True, description="Режим отладки")
    LOG_LEVEL: str = Field(default="INFO", description="Уровень логирования")
    BACKEND_URL: str = Field(
        default="http://localhost:8000", description="URL бэкенд-приложения"
    )

    # NLP Service
    NLP_SERVICE_URL: str = Field(
        default="http://localhost:8080", description="URL NLP-сервиса"
    )
    NLP_SERVICE_API_KEY: str = Field(
        default="", description="API ключ для NLP-сервиса"
    )

    # File Storage
    FILE_STORAGE_PATH: str = Field(
        default="./storage", description="Путь к хранилищу файлов"
    )
    MAX_FILE_SIZE: int = Field(
        default=52428800, description="Максимальный размер файла в байтах (50 МБ)"
    )
    ALLOWED_FILE_TYPES: str = Field(
        default="application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg,image/png",
        description="Разрешенные типы файлов через запятую",
    )

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Разрешенные источники для CORS (через запятую)",
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Возвращает список разрешенных источников для CORS."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_file_types_list(self) -> List[str]:
        """Возвращает список разрешенных типов файлов."""
        return [t.strip() for t in self.ALLOWED_FILE_TYPES.split(",")]
    
    class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"  # Игнорировать лишние переменные окружения


settings = Settings()

