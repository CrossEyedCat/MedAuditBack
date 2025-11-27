"""
Сервис аутентификации.
"""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin
from app.utils.password import verify_password, get_password_hash
from app.utils.jwt import create_access_token, create_refresh_token
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Сервис для работы с аутентификацией."""

    @staticmethod
    async def register_user(db: AsyncSession, user_data: UserRegister) -> User:
        """
        Регистрация нового пользователя.

        Args:
            db: Сессия БД
            user_data: Данные пользователя

        Returns:
            Созданный пользователь

        Raises:
            ValueError: Если email уже существует
        """
        # Проверка существования пользователя
        existing_user = await AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise ValueError("Пользователь с таким email уже существует")

        # Создание пользователя
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True,
        )

        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            logger.info("User registered", user_id=str(new_user.id), email=new_user.email)
            return new_user
        except IntegrityError:
            await db.rollback()
            raise ValueError("Пользователь с таким email уже существует")

    @staticmethod
    async def authenticate_user(db: AsyncSession, user_data: UserLogin) -> User | None:
        """
        Аутентификация пользователя.

        Args:
            db: Сессия БД
            user_data: Данные для входа

        Returns:
            Пользователь или None если неверные учетные данные
        """
        user = await AuthService.get_user_by_email(db, user_data.email)
        if not user:
            logger.warning("Login attempt with non-existent email", email=user_data.email)
            return None

        if not user.is_active:
            logger.warning("Login attempt for inactive user", user_id=str(user.id))
            return None

        if not verify_password(user_data.password, user.password_hash):
            logger.warning("Invalid password attempt", user_id=str(user.id))
            return None

        logger.info("User authenticated", user_id=str(user.id), email=user.email)
        return user

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
        """
        Получение пользователя по email.

        Args:
            db: Сессия БД
            email: Email пользователя

        Returns:
            Пользователь или None
        """
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
        """
        Получение пользователя по ID.

        Args:
            db: Сессия БД
            user_id: ID пользователя

        Returns:
            Пользователь или None
        """
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    def create_tokens(user: User) -> dict:
        """
        Создание токенов для пользователя.

        Args:
            user: Пользователь

        Returns:
            Словарь с access_token и refresh_token
        """
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }





