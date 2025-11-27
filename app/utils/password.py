"""
Утилиты для работы с паролями.
"""
from passlib.context import CryptContext

# Контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля.

    Args:
        plain_password: Обычный пароль
        hashed_password: Хешированный пароль

    Returns:
        True если пароль верный, иначе False
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Хеширование пароля.

    Args:
        password: Обычный пароль

    Returns:
        Хешированный пароль
    """
    return pwd_context.hash(password)





