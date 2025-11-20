"""
Сервис для взаимодействия с NLP-сервисом.
"""
import httpx
from uuid import UUID
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.nlp import NLPRequest, NLPCallbackRequest

logger = get_logger(__name__)


class NLPService:
    """Сервис для взаимодействия с NLP-сервисом."""

    @staticmethod
    async def send_document_for_analysis(
        request_id: UUID,
        document_id: UUID,
        file_url: str,
        callback_url: str,
    ) -> Dict[str, Any]:
        """
        Отправка документа на анализ в NLP-сервис.

        Args:
            request_id: UUID запроса
            document_id: UUID документа
            file_url: URL файла или base64
            callback_url: URL для callback

        Returns:
            Ответ от NLP-сервиса

        Raises:
            httpx.HTTPError: При ошибке HTTP запроса
            Exception: При других ошибках
        """
        request_data = NLPRequest(
            request_id=request_id,
            document_id=document_id,
            file_url=file_url,
            callback_url=callback_url,
        )

        headers = {
            "Content-Type": "application/json",
        }

        # Добавляем API ключ, если он указан
        if settings.NLP_SERVICE_API_KEY:
            headers["Authorization"] = f"Bearer {settings.NLP_SERVICE_API_KEY}"

        url = f"{settings.NLP_SERVICE_URL}/api/analyze"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(
                    "Sending document to NLP service",
                    request_id=str(request_id),
                    document_id=str(document_id),
                    url=url,
                )

                response = await client.post(
                    url,
                    json=request_data.model_dump(),
                    headers=headers,
                )

                response.raise_for_status()
                result = response.json()

                logger.info(
                    "Document sent to NLP service successfully",
                    request_id=str(request_id),
                    status_code=response.status_code,
                )

                return result

        except httpx.TimeoutException as e:
            logger.error(
                "NLP service timeout",
                request_id=str(request_id),
                error=str(e),
            )
            raise Exception(f"Таймаут при обращении к NLP-сервису: {str(e)}")

        except httpx.HTTPStatusError as e:
            logger.error(
                "NLP service HTTP error",
                request_id=str(request_id),
                status_code=e.response.status_code,
                error=str(e),
            )
            raise Exception(f"Ошибка NLP-сервиса (HTTP {e.response.status_code}): {str(e)}")

        except httpx.RequestError as e:
            logger.error(
                "NLP service request error",
                request_id=str(request_id),
                error=str(e),
            )
            raise Exception(f"Ошибка при обращении к NLP-сервису: {str(e)}")

        except Exception as e:
            logger.error(
                "Unexpected error sending to NLP service",
                request_id=str(request_id),
                error=str(e),
            )
            raise

    @staticmethod
    def parse_callback_data(callback_data: Dict[str, Any]) -> NLPCallbackRequest:
        """
        Парсинг данных callback от NLP-сервиса.

        Args:
            callback_data: Данные callback

        Returns:
            Распарсенные данные

        Raises:
            ValueError: Если данные невалидны
        """
        try:
            return NLPCallbackRequest(**callback_data)
        except Exception as e:
            logger.error("Error parsing NLP callback data", error=str(e), data=callback_data)
            raise ValueError(f"Ошибка парсинга данных callback: {str(e)}")

    @staticmethod
    def build_file_url(document_id: UUID, stored_filename: str) -> str:
        """
        Построение URL файла для отправки в NLP-сервис.

        Args:
            document_id: ID документа
            stored_filename: Имя сохраненного файла

        Returns:
            URL файла
        """
        # В production это должен быть URL к файлу в объектном хранилище (S3 и т.д.)
        # Пока используем локальный URL
        base_url = settings.BACKEND_URL.rstrip("/")
        return f"{base_url}/api/v1/documents/{document_id}/download"


