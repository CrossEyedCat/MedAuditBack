"""
Утилиты для работы с файлами.
"""
import hashlib
import os
import uuid
from pathlib import Path
from typing import Tuple, Optional

import aiofiles
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_file_type(mime_type: str) -> bool:
    """
    Проверка типа файла.

    Args:
        mime_type: MIME-тип файла

    Returns:
        True если тип разрешен, иначе False
    """
    allowed_types = settings.allowed_file_types_list
    return mime_type in allowed_types


def validate_file_size(file_size: int) -> bool:
    """
    Проверка размера файла.

    Args:
        file_size: Размер файла в байтах

    Returns:
        True если размер допустим, иначе False
    """
    return file_size <= settings.MAX_FILE_SIZE


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от опасных символов.

    Args:
        filename: Исходное имя файла

    Returns:
        Очищенное имя файла
    """
    from app.utils.validation import sanitize_filename as validate_sanitize
    return validate_sanitize(filename)


async def calculate_file_hash(file_content: bytes) -> str:
    """
    Вычисление SHA-256 хеша файла.

    Args:
        file_content: Содержимое файла

    Returns:
        SHA-256 хеш в hex формате
    """
    return hashlib.sha256(file_content).hexdigest()


async def save_file(file: UploadFile, file_content: bytes) -> Tuple[str, str]:
    """
    Сохранение файла на диск.

    Args:
        file: Загружаемый файл
        file_content: Содержимое файла

    Returns:
        Кортеж (stored_filename, file_path)
    """
    # Создаем директорию для хранения файлов
    storage_path = Path(settings.FILE_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Генерируем уникальное имя файла
    file_extension = Path(file.filename).suffix
    stored_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = storage_path / stored_filename

    # Сохраняем файл
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_content)

    logger.info("File saved", stored_filename=stored_filename, file_path=str(file_path))
    return stored_filename, str(file_path)


async def read_file(file_path: str) -> bytes:
    """
    Чтение файла с диска.

    Args:
        file_path: Путь к файлу

    Returns:
        Содержимое файла

    Raises:
        HTTPException: Если файл не найден
    """
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден",
        )

    async with aiofiles.open(file_path, 'rb') as f:
        return await f.read()


async def delete_file(file_path: str) -> None:
    """
    Удаление файла с диска.

    Args:
        file_path: Путь к файлу
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info("File deleted", file_path=file_path)
    except OSError as e:
        logger.error("Error deleting file", file_path=file_path, error=str(e))


def get_file_path(stored_filename: str) -> str:
    """
    Получение полного пути к файлу.

    Args:
        stored_filename: Имя сохраненного файла

    Returns:
        Полный путь к файлу
    """
    storage_path = Path(settings.FILE_STORAGE_PATH)
    return str(storage_path / stored_filename)


async def validate_upload_file(file: UploadFile) -> Tuple[bytes, str]:
    """
    Валидация и чтение загружаемого файла.

    Args:
        file: Загружаемый файл

    Returns:
        Кортеж (file_content, mime_type)

    Raises:
        HTTPException: Если файл невалиден
    """
    # Проверка типа файла
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось определить тип файла",
        )

    if not validate_file_type(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Тип файла не разрешен. Разрешенные типы: {', '.join(settings.allowed_file_types_list)}",
        )

    # Чтение содержимого файла
    file_content = await file.read()

    # Проверка размера файла
    file_size = len(file_content)
    if not validate_file_size(file_size):
        max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Размер файла превышает максимально допустимый ({max_size_mb} МБ)",
        )

    return file_content, file.content_type

