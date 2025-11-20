"""
Endpoints для аутентификации.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.dependencies import get_current_user
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    TokenRefresh,
    UserResponse,
    MessageResponse,
)
from app.services.auth import AuthService
from app.utils.jwt import decode_token, get_user_id_from_token
from app.models.user import User
from app.core.logging import get_logger

security = HTTPBearer()

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Регистрация нового пользователя в системе",
)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Регистрация нового пользователя.

    Args:
        user_data: Данные для регистрации
        db: Сессия БД

    Returns:
        Токены доступа

    Raises:
        HTTPException: Если пользователь уже существует или данные невалидны
    """
    try:
        user = await AuthService.register_user(db, user_data)
        tokens = AuthService.create_tokens(user)
        logger.info(
            "User registered successfully",
            user_id=str(user.id),
            email=user.email,
            ip_address=getattr(request.client, "host", "unknown") if hasattr(request, "client") else "unknown",
        )
        return TokenResponse(**tokens)
    except ValueError as e:
        logger.warning(
            "Registration failed",
            email=user_data.email,
            error=str(e),
            ip_address=getattr(request.client, "host", "unknown") if hasattr(request, "client") else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход пользователя",
    description="Аутентификация пользователя и получение токенов",
)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Вход пользователя в систему.

    Args:
        user_data: Данные для входа
        db: Сессия БД

    Returns:
        Токены доступа

    Raises:
        HTTPException: Если учетные данные неверны
    """
    user = await AuthService.authenticate_user(db, user_data)
    if not user:
        logger.warning(
            "Login failed - invalid credentials",
            email=user_data.email,
            ip_address=getattr(request.client, "host", "unknown") if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = AuthService.create_tokens(user)
    logger.info(
        "User logged in successfully",
        user_id=str(user.id),
        email=user.email,
        ip_address=getattr(request.client, "host", "unknown") if request.client else "unknown",
    )
    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токенов",
    description="Обновление access token с помощью refresh token",
)
async def refresh(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Обновление токенов доступа.

    Args:
        token_data: Refresh token
        db: Сессия БД
        redis: Клиент Redis

    Returns:
        Новые токены доступа

    Raises:
        HTTPException: Если refresh token невалидный
    """
    refresh_token = token_data.refresh_token

    # Проверка токена в blacklist
    is_blacklisted = await redis.get(f"blacklist:{refresh_token}")
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен был отозван",
        )

    # Декодирование токена
    payload = decode_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный refresh token",
        )

    # Проверка типа токена
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный тип токена",
        )

    # Получение пользователя
    user_id = get_user_id_from_token(refresh_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    user = await AuthService.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен",
        )

    # Создание новых токенов
    tokens = AuthService.create_tokens(user)
    return TokenResponse(**tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход пользователя",
    description="Выход пользователя и добавление токенов в blacklist",
)
async def logout(
    token_data: TokenRefresh,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis),
) -> MessageResponse:
    """
    Выход пользователя из системы.

    Args:
        token_data: Refresh token для добавления в blacklist
        credentials: Access token из заголовка Authorization
        current_user: Текущий пользователь
        redis: Клиент Redis

    Returns:
        Сообщение об успешном выходе
    """
    access_token = credentials.credentials
    refresh_token = token_data.refresh_token

    # Добавление access token в blacklist
    access_payload = decode_token(access_token)
    if access_payload and "exp" in access_payload:
        exp_time = access_payload["exp"]
        current_time = int(datetime.utcnow().timestamp())
        ttl = exp_time - current_time
        if ttl > 0:
            await redis.setex(f"blacklist:{access_token}", ttl, "1")

    # Добавление refresh token в blacklist
    refresh_payload = decode_token(refresh_token)
    if refresh_payload and "exp" in refresh_payload:
        exp_time = refresh_payload["exp"]
        current_time = int(datetime.utcnow().timestamp())
        ttl = exp_time - current_time
        if ttl > 0:
            await redis.setex(f"blacklist:{refresh_token}", ttl, "1")

    logger.info("User logged out", user_id=str(current_user.id))
    return MessageResponse(message="Успешный выход из системы")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Информация о текущем пользователе",
    description="Получение информации о текущем аутентифицированном пользователе",
)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Получение информации о текущем пользователе.

    Args:
        current_user: Текущий пользователь

    Returns:
        Информация о пользователе
    """
    return UserResponse.model_validate(current_user)

