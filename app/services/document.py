"""
Сервис для работы с документами.
"""
from uuid import UUID
from typing import Optional, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentFilterParams
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Сервис для работы с документами."""

    @staticmethod
    async def create_document(
        db: AsyncSession,
        user_id: UUID,
        original_filename: str,
        stored_filename: str,
        file_size: int,
        mime_type: str,
        file_hash: str,
    ) -> Document:
        """
        Создание записи о документе в БД.

        Args:
            db: Сессия БД
            user_id: ID пользователя
            original_filename: Оригинальное имя файла
            stored_filename: Имя сохраненного файла
            file_size: Размер файла
            mime_type: MIME-тип файла
            file_hash: SHA-256 хеш файла

        Returns:
            Созданный документ
        """
        document = Document(
            user_id=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            status=DocumentStatus.PENDING,
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)
        logger.info("Document created", document_id=str(document.id), user_id=str(user_id))
        return document

    @staticmethod
    async def get_document_by_id(
        db: AsyncSession,
        document_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Document]:
        """
        Получение документа по ID.

        Args:
            db: Сессия БД
            document_id: ID документа
            user_id: ID пользователя (опционально, для проверки прав доступа)

        Returns:
            Документ или None
        """
        query = select(Document).where(Document.id == document_id)
        if user_id:
            query = query.where(Document.user_id == user_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_documents_by_user(
        db: AsyncSession,
        user_id: UUID,
        filters: DocumentFilterParams,
    ) -> Tuple[List[Document], int]:
        """
        Получение списка документов пользователя с фильтрацией и пагинацией.

        Args:
            db: Сессия БД
            user_id: ID пользователя
            filters: Параметры фильтрации

        Returns:
            Кортеж (список документов, общее количество)
        """
        # Базовый запрос
        query = select(Document).where(Document.user_id == user_id)
        count_query = select(func.count()).select_from(Document).where(Document.user_id == user_id)

        # Применение фильтров
        if filters.status:
            try:
                status_enum = DocumentStatus(filters.status)
                query = query.where(Document.status == status_enum)
                count_query = count_query.where(Document.status == status_enum)
            except ValueError:
                pass  # Игнорируем невалидный статус

        if filters.mime_type:
            query = query.where(Document.mime_type == filters.mime_type)
            count_query = count_query.where(Document.mime_type == filters.mime_type)

        # Подсчет общего количества
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Сортировка
        order_column = getattr(Document, filters.order_by, Document.created_at)
        if filters.order_direction == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # Пагинация
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Выполнение запроса
        result = await db.execute(query)
        documents = result.scalars().all()

        return list(documents), total

    @staticmethod
    async def check_duplicate_by_hash(
        db: AsyncSession,
        file_hash: str,
        user_id: UUID,
    ) -> Optional[Document]:
        """
        Проверка наличия документа с таким же хешем у пользователя.

        Args:
            db: Сессия БД
            file_hash: SHA-256 хеш файла
            user_id: ID пользователя

        Returns:
            Существующий документ или None
        """
        result = await db.execute(
            select(Document).where(
                and_(
                    Document.file_hash == file_hash,
                    Document.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Удаление документа.

        Args:
            db: Сессия БД
            document_id: ID документа
            user_id: ID пользователя

        Returns:
            True если документ удален, False если не найден
        """
        document = await DocumentService.get_document_by_id(db, document_id, user_id)
        if not document:
            return False

        await db.delete(document)
        await db.commit()
        logger.info("Document deleted", document_id=str(document_id), user_id=str(user_id))
        return True

    @staticmethod
    async def update_document_status(
        db: AsyncSession,
        document_id: UUID,
        status: DocumentStatus,
    ) -> Optional[Document]:
        """
        Обновление статуса документа.

        Args:
            db: Сессия БД
            document_id: ID документа
            status: Новый статус

        Returns:
            Обновленный документ или None
        """
        document = await DocumentService.get_document_by_id(db, document_id)
        if not document:
            return None

        document.status = status
        await db.commit()
        await db.refresh(document)
        logger.info("Document status updated", document_id=str(document_id), status=status.value)
        return document


