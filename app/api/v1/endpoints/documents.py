"""
Endpoints для работы с документами.
"""
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUploadResponse,
    DocumentFilterParams,
)
from app.services.document import DocumentService
from app.services.cache import CacheService
from app.utils.file import (
    validate_upload_file,
    save_file,
    calculate_file_hash,
    sanitize_filename,
    get_file_path,
    delete_file,
)
from app.utils.image_optimizer import optimize_image
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Загрузка документа",
    description="Загрузка документа в систему с валидацией типа и размера",
)
async def upload_document(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """
    Загрузка документа.

    Args:
        file: Загружаемый файл
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Информация о загруженном документе

    Raises:
        HTTPException: Если файл невалиден или дубликат
    """
    # Валидация и чтение файла
    file_content, mime_type = await validate_upload_file(file)

    # Оптимизация изображений (если это изображение)
    if mime_type in ("image/jpeg", "image/png"):
        try:
            optimized_content = await optimize_image(file_content)
            if optimized_content and len(optimized_content) < len(file_content):
                file_content = optimized_content
                logger.info(
                    "Image optimized during upload",
                    original_size=len(file_content),
                    optimized_size=len(optimized_content),
                )
        except Exception as e:
            logger.warning("Error optimizing image, using original", error=str(e))

    # Вычисление хеша
    file_hash = await calculate_file_hash(file_content)

    # Проверка на дубликаты
    existing_document = await DocumentService.check_duplicate_by_hash(
        db, file_hash, current_user.id
    )
    if existing_document:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Документ с таким содержимым уже существует",
        )

    # Очистка имени файла
    sanitized_filename = sanitize_filename(file.filename or "unnamed")

    # Сохранение файла
    stored_filename, file_path = await save_file(file, file_content)

    try:
        # Создание записи в БД
        document = await DocumentService.create_document(
            db=db,
            user_id=current_user.id,
            original_filename=sanitized_filename,
            stored_filename=stored_filename,
            file_size=len(file_content),
            mime_type=mime_type,
            file_hash=file_hash,
        )

        logger.info(
            "Document uploaded",
            document_id=str(document.id),
            user_id=str(current_user.id),
            filename=sanitized_filename,
            file_size=len(file_content),
            mime_type=mime_type,
            ip_address=getattr(request.client, "host", "unknown") if request and request.client else "unknown",
        )

        response_data = DocumentResponse.model_validate(document)
        
        # Инвалидируем кеш списков документов пользователя
        await CacheService.delete_pattern(f"documents:user:{current_user.id}:*")
        
        return DocumentUploadResponse(**response_data.model_dump(), message="Документ успешно загружен")

    except Exception as e:
        # В случае ошибки удаляем сохраненный файл
        await delete_file(file_path)
        logger.error("Error uploading document", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при загрузке документа",
        )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="Список документов",
    description="Получение списка документов пользователя с пагинацией и фильтрацией",
)
async def get_documents(
    status: str | None = None,
    mime_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
    order_by: str = "created_at",
    order_direction: str = "desc",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """
    Получение списка документов пользователя.

    Args:
        status: Фильтр по статусу (pending, processing, completed, failed)
        mime_type: Фильтр по типу файла
        page: Номер страницы
        page_size: Размер страницы
        order_by: Поле для сортировки
        order_direction: Направление сортировки (asc/desc)
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Список документов с метаданными пагинации
    """
    filters = DocumentFilterParams(
        status=status,
        mime_type=mime_type,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction,
    )

    # Проверяем кеш для стандартных запросов
    cache_key = f"documents:user:{current_user.id}:page:{page}:size:{page_size}:status:{status}:mime:{mime_type}"
    if not mime_type:  # Кешируем только простые запросы
        cached_result = await CacheService.get(cache_key)
        if cached_result:
            return DocumentListResponse(**cached_result)

    documents, total = await DocumentService.get_documents_by_user(db, current_user.id, filters)
    pages = math.ceil(total / page_size) if total > 0 else 0

    result = DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

    # Сохраняем в кеш
    if not mime_type:
        await CacheService.set(cache_key, result.model_dump(), ttl=300)  # 5 минут

    return result


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Информация о документе",
    description="Получение детальной информации о документе",
)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """
    Получение информации о документе.

    Args:
        document_id: ID документа
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Информация о документе

    Raises:
        HTTPException: Если документ не найден или нет прав доступа
    """
    # Проверяем кеш
    cache_key = f"document:{document_id}:user:{current_user.id}"
    cached_result = await CacheService.get(cache_key)
    if cached_result:
        return DocumentResponse(**cached_result)

    document = await DocumentService.get_document_by_id(db, document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    result = DocumentResponse.model_validate(document)
    
    # Сохраняем в кеш
    await CacheService.set(cache_key, result.model_dump(), ttl=600)  # 10 минут

    return result


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление документа",
    description="Удаление документа и связанного файла",
)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Удаление документа.

    Args:
        document_id: ID документа
        current_user: Текущий пользователь
        db: Сессия БД

    Raises:
        HTTPException: Если документ не найден или нет прав доступа
    """
    # Получаем документ для получения пути к файлу
    document = await DocumentService.get_document_by_id(db, document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    # Удаляем файл с диска
    file_path = get_file_path(document.stored_filename)
    await delete_file(file_path)

    # Удаляем запись из БД
    deleted = await DocumentService.delete_document(db, document_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    # Инвалидируем кеш
    await CacheService.delete(f"document:{document_id}:user:{current_user.id}")
    await CacheService.delete_pattern(f"documents:user:{current_user.id}:*")

    logger.info("Document deleted", document_id=str(document_id), user_id=str(current_user.id))


@router.get(
    "/{document_id}/download",
    summary="Скачивание документа",
    description="Скачивание файла документа",
)
async def download_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Скачивание документа.

    Args:
        document_id: ID документа
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Файл для скачивания

    Raises:
        HTTPException: Если документ не найден или нет прав доступа
    """
    document = await DocumentService.get_document_by_id(db, document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден",
        )

    file_path = get_file_path(document.stored_filename)

    # Проверка существования файла
    import os
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден на сервере",
        )

    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type=document.mime_type,
    )

