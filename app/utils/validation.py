"""
Утилиты для валидации и санитизации данных.
"""
import re
from pathlib import Path
from typing import Optional

from pydantic import field_validator, ValidationError


def sanitize_filename(filename: str) -> str:
    """
    Санитизация имени файла.

    Args:
        filename: Исходное имя файла

    Returns:
        Очищенное имя файла
    """
    if not filename:
        return "unnamed"

    # Удаляем путь, оставляем только имя файла
    filename = Path(filename).name

    # Удаляем опасные символы
    dangerous_chars = ['/', '\\', '..', '\x00', '<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')

    # Ограничиваем длину
    max_length = 255
    if len(filename) > max_length:
        name, ext = Path(filename).stem[:max_length-10], Path(filename).suffix
        filename = f"{name}{ext}"

    return filename


def validate_file_path(file_path: str, base_path: str) -> bool:
    """
    Проверка пути файла на path traversal атаки.

    Args:
        file_path: Путь к файлу
        base_path: Базовый путь хранилища

    Returns:
        True если путь безопасен, иначе False
    """
    try:
        # Нормализуем пути
        resolved_path = Path(base_path).resolve() / file_path
        base_resolved = Path(base_path).resolve()

        # Проверяем, что файл находится внутри базового пути
        return base_resolved in resolved_path.parents or resolved_path == base_resolved
    except Exception:
        return False


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Санитизация строки.

    Args:
        value: Исходная строка
        max_length: Максимальная длина

    Returns:
        Очищенная строка
    """
    if not value:
        return ""

    # Удаляем управляющие символы
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)

    # Обрезаем длину
    if max_length and len(value) > max_length:
        value = value[:max_length]

    return value.strip()


def validate_email(email: str) -> bool:
    """
    Валидация email адреса.

    Args:
        email: Email адрес

    Returns:
        True если email валиден
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(uuid_string: str) -> bool:
    """
    Валидация UUID.

    Args:
        uuid_string: UUID в виде строки

    Returns:
        True если UUID валиден
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_string.lower()))





