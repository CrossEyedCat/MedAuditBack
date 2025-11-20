"""
Утилиты для оптимизации изображений.
"""
from io import BytesIO
from typing import Optional
from PIL import Image

from app.core.logging import get_logger

logger = get_logger(__name__)


async def optimize_image(
    image_content: bytes,
    max_width: Optional[int] = 1920,
    max_height: Optional[int] = 1080,
    quality: int = 85,
) -> Optional[bytes]:
    """
    Оптимизация изображения (сжатие и изменение размера).

    Args:
        image_content: Содержимое изображения
        max_width: Максимальная ширина
        max_height: Максимальная высота
        quality: Качество JPEG (1-100)

    Returns:
        Оптимизированное изображение или None при ошибке
    """
    try:
        # Открываем изображение
        image = Image.open(BytesIO(image_content))
        original_format = image.format

        # Изменяем размер если нужно
        if max_width or max_height:
            image.thumbnail((max_width or image.width, max_height or image.height), Image.Resampling.LANCZOS)

        # Конвертируем в RGB если нужно (для JPEG)
        if image.mode in ("RGBA", "P") and original_format in ("PNG", "JPEG"):
            # Создаем белый фон для прозрачных изображений
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "RGBA":
                rgb_image.paste(image, mask=image.split()[3])  # Используем альфа-канал как маску
            else:
                rgb_image.paste(image)
            image = rgb_image

        # Сохраняем в буфер
        output = BytesIO()
        
        if original_format == "JPEG" or image.mode == "RGB":
            image.save(output, format="JPEG", quality=quality, optimize=True)
        else:
            image.save(output, format=original_format, optimize=True)

        output.seek(0)
        optimized_content = output.read()

        # Логируем результат оптимизации
        original_size = len(image_content)
        optimized_size = len(optimized_content)
        compression_ratio = (1 - optimized_size / original_size) * 100

        if compression_ratio > 10:  # Значительное сжатие
            logger.info(
                "Image optimized",
                original_size=original_size,
                optimized_size=optimized_size,
                compression_ratio=f"{compression_ratio:.1f}%",
            )

        return optimized_content

    except Exception as e:
        logger.warning("Error optimizing image", error=str(e))
        # Возвращаем оригинал при ошибке
        return image_content


