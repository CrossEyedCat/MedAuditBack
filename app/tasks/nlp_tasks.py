"""
Celery задачи для обработки документов через NLP-сервис.
"""
import asyncio
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import DocumentStatus
from app.models.audit_report import AuditReport, AuditReportStatus
from app.services.nlp import NLPService
from app.services.document import DocumentService

logger = get_logger(__name__)

# Создание async движка для Celery задач
db_engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(
    bind=True,
    name="process_document_with_nlp",
    max_retries=3,
    default_retry_delay=60,
)
def process_document_with_nlp(self, document_id: str) -> dict:
    """
    Обработка документа через NLP-сервис.

    Args:
        document_id: UUID документа в виде строки

    Returns:
        Результат обработки
    """
    try:
        # Запускаем асинхронную функцию
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_process_document_async(UUID(document_id)))
        return result
    except Exception as exc:
        logger.error(
            "Error processing document with NLP",
            document_id=document_id,
            error=str(exc),
            exc_info=True,
        )
        # Повторная попытка с экспоненциальной задержкой
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


async def _process_document_async(document_id: UUID) -> dict:
    """Асинхронная часть обработки документа."""
    async with SessionLocal() as db:
        try:
            # Получаем документ
            document = await DocumentService.get_document_by_id(db, document_id)
            if not document:
                raise ValueError(f"Документ {document_id} не найден")

            # Проверяем, не создан ли уже отчет для этого документа
            existing_report = await db.execute(
                select(AuditReport).where(
                    AuditReport.document_id == document_id,
                    AuditReport.status.in_([AuditReportStatus.PENDING, AuditReportStatus.PROCESSING]),
                )
            )
            audit_report = existing_report.scalar_one_or_none()

            if not audit_report:
                # Генерируем request_id и создаем запись AuditReport
                request_id = uuid4()
                audit_report = AuditReport(
                    document_id=document_id,
                    request_id=request_id,
                    status=AuditReportStatus.PENDING,
                )
                db.add(audit_report)
                await db.commit()
                await db.refresh(audit_report)
            else:
                request_id = audit_report.request_id

            logger.info(
                "Audit report created",
                audit_report_id=str(audit_report.id),
                document_id=str(document_id),
                request_id=str(request_id),
            )

            # Обновляем статус документа
            await DocumentService.update_document_status(db, document_id, DocumentStatus.PROCESSING)

            # Обновляем статус отчета
            audit_report.status = AuditReportStatus.PROCESSING
            await db.commit()

            # Строим URL файла
            file_url = NLPService.build_file_url(document_id, document.stored_filename)

            # Строим callback URL
            callback_url = f"{settings.BACKEND_URL}/api/v1/nlp/callback"

            # Отправляем запрос в NLP-сервис
            try:
                await NLPService.send_document_for_analysis(
                    request_id=request_id,
                    document_id=document_id,
                    file_url=file_url,
                    callback_url=callback_url,
                )

                logger.info(
                    "Document sent to NLP service",
                    document_id=str(document_id),
                    request_id=str(request_id),
                )

                return {
                    "status": "sent",
                    "request_id": str(request_id),
                    "document_id": str(document_id),
                }

            except Exception as e:
                # Ошибка при отправке в NLP-сервис
                logger.error(
                    "Error sending to NLP service",
                    document_id=str(document_id),
                    request_id=str(request_id),
                    error=str(e),
                )

                # Обновляем статусы
                audit_report.status = AuditReportStatus.FAILED
                audit_report.error_message = str(e)
                await DocumentService.update_document_status(db, document_id, DocumentStatus.FAILED)
                await db.commit()

                raise
        except Exception as e:
            # Общая обработка ошибок
            await db.rollback()
            raise

