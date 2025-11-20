"""
Зависимости FastAPI для защиты endpoints.
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis, Redis
from app.models.user import User
from app.utils.jwt import decode_token, get_user_id_from_token
from app.services.auth import AuthService
from app.core.logging import get_logger

logger = get_logger(__name__)

# Схема для извлечения токена из заголовка
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Получение текущего пользователя из JWT токена.

    Args:
        credentials: Учетные данные из заголовка Authorization
        db: Сессия БД
        redis: Клиент Redis

    Returns:
        Текущий пользователь

    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    token = credentials.credentials

    # Проверка токена в blacklist
    is_blacklisted = await redis.get(f"blacklist:{token}")
    if is_blacklisted:
        logger.warning("Attempt to use blacklisted token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Декодирование токена
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка типа токена
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получение ID пользователя
    user_id: Optional[UUID] = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получение пользователя из БД
    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Получение активного пользователя.

    Args:
        current_user: Текущий пользователь

    Returns:
        Активный пользователь

    Raises:
        HTTPException: Если пользователь неактивен
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )
    return current_user

