"""
Pydantic схемы для аутентификации.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Схема для регистрации пользователя."""

    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., min_length=8, max_length=100, description="Пароль (мин. 8 символов)")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Валидация пароля."""
        if len(v) < 8:
            raise ValueError("Пароль должен содержать минимум 8 символов")
        if not any(c.isdigit() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(c.isalpha() for c in v):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        return v


class UserLogin(BaseModel):
    """Схема для входа пользователя."""

    email: EmailStr = Field(..., description="Email пользователя")
    password: str = Field(..., description="Пароль")


class TokenResponse(BaseModel):
    """Схема ответа с токенами."""

    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Тип токена")


class TokenRefresh(BaseModel):
    """Схема для обновления токена."""

    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """Схема ответа с информацией о пользователе."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Схема для сообщений об успехе."""

    message: str = Field(..., description="Сообщение")


