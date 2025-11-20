"""
Endpoints для работы с отчетами об аудите.
"""
import math
from uuid import UUID
from datetime import datetime
from io import BytesIO

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.document import Document
from app.schemas.report import (
    ReportGenerateRequest,
    ReportGenerateResponse,
    AuditReportResponse,
    AuditReportListResponse,
    AuditReportListItem,
    ReportFilterParams,
    ViolationFilterParams,
    ViolationResponse,
)
from app.services.report import ReportService
from app.services.document import DocumentService
from app.services.cache import CacheService
from app.tasks.nlp_tasks import process_document_with_nlp
from app.utils.pdf_generator import generate_pdf_report
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/generate",
    response_model=ReportGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Запуск анализа документа",
    description="Запуск процесса анализа документа через NLP-сервис",
)
async def generate_report(
    request: ReportGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportGenerateResponse:
    """
    Запуск анализа документа.

    Args:
        request: Данные запроса с document_id
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Информация о созданном отчете

    Raises:
        HTTPException: Если документ не найден или нет прав доступа
    """
    # Проверка существования документа и прав доступа
    document = await DocumentService.get_document_by_id(db, request.document_id, current_user.id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Документ не найден или нет прав доступа",
        )

    # Проверка, не запущен ли уже анализ для этого документа
    existing_report = await db.execute(
        select(AuditReport)
        .where(
            AuditReport.document_id == request.document_id,
            AuditReport.status.in_([AuditReportStatus.PENDING, AuditReportStatus.PROCESSING]),
        )
    )
    if existing_report.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Анализ документа уже запущен",
        )

    # Создание отчета (request_id будет создан в Celery задаче)
    from uuid import uuid4
    request_id = uuid4()
    audit_report = await ReportService.create_audit_report(db, request.document_id, request_id)

    # Запуск Celery задачи
    try:
        task = process_document_with_nlp.delay(str(request.document_id))
        logger.info(
            "Analysis task started",
            audit_report_id=str(audit_report.id),
            document_id=str(request.document_id),
            task_id=task.id,
        )
    except Exception as e:
        logger.error("Error starting analysis task", error=str(e))
        # Обновляем статус отчета на failed
        audit_report.status = AuditReportStatus.FAILED
        audit_report.error_message = f"Ошибка запуска задачи: {str(e)}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при запуске анализа",
        )

    return ReportGenerateResponse(
        id=audit_report.id,
        document_id=audit_report.document_id,
        status=audit_report.status.value,
        message="Анализ документа запущен",
    )


@router.get(
    "/",
    response_model=AuditReportListResponse,
    summary="Список отчетов",
    description="Получение списка отчетов пользователя с пагинацией и фильтрацией",
)
async def get_reports(
    status: str | None = Query(None, description="Фильтр по статусу"),
    document_id: UUID | None = Query(None, description="Фильтр по ID документа"),
    risk_level: str | None = Query(None, description="Фильтр по уровню риска"),
    date_from: datetime | None = Query(None, description="Фильтр по дате создания (от)"),
    date_to: datetime | None = Query(None, description="Фильтр по дате создания (до)"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    order_by: str = Query("created_at", description="Поле для сортировки"),
    order_direction: str = Query("desc", pattern="^(asc|desc)$", description="Направление сортировки"),
    include_violations: bool = Query(False, description="Включить нарушения в ответ"),
    include_summary: bool = Query(True, description="Включить сводку в ответ"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditReportListResponse:
    """
    Получение списка отчетов пользователя.

    Args:
        status: Фильтр по статусу
        document_id: Фильтр по ID документа
        risk_level: Фильтр по уровню риска нарушений
        date_from: Фильтр по дате создания (от)
        date_to: Фильтр по дате создания (до)
        page: Номер страницы
        page_size: Размер страницы
        order_by: Поле для сортировки
        order_direction: Направление сортировки
        include_violations: Включить нарушения в ответ
        include_summary: Включить сводку в ответ
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Список отчетов с метаданными пагинации
    """
    filters = ReportFilterParams(
        status=status,
        document_id=document_id,
        risk_level=risk_level,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        order_by=order_by,
        order_direction=order_direction,
        include_violations=include_violations,
        include_summary=include_summary,
    )

    # Проверяем кеш (только для стандартных запросов без сложных фильтров)
    cache_key = f"reports:user:{current_user.id}:page:{page}:size:{page_size}:status:{status}"
    if not risk_level and not document_id and not date_from and not date_to:
        cached_result = await CacheService.get(cache_key)
        if cached_result:
            return AuditReportListResponse(**cached_result)

    reports, total = await ReportService.get_reports_by_user(db, current_user.id, filters)
    pages = math.ceil(total / page_size) if total > 0 else 0

    # Формируем список элементов с дополнительными данными
    items = []
    for report in reports:
        # Получаем количество нарушений
        violations_count = len(report.violations) if report.violations else 0

        # Получаем compliance_score из summary
        compliance_score = None
        if report.analysis_summary:
            compliance_score = report.analysis_summary.compliance_score

        # Получаем имя файла документа
        document_filename = None
        if report.document:
            document_filename = report.document.original_filename

        items.append(
            AuditReportListItem(
                id=report.id,
                document_id=report.document_id,
                status=report.status.value,
                created_at=report.created_at,
                completed_at=report.completed_at,
                compliance_score=compliance_score,
                violations_count=violations_count,
                document_filename=document_filename,
            )
        )

    result = AuditReportListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

    # Сохраняем в кеш (только для стандартных запросов)
    if not risk_level and not document_id and not date_from and not date_to:
        await CacheService.set(cache_key, result.model_dump(), ttl=300)  # 5 минут

    return result


@router.post("/{report_id}/invalidate-cache")
async def invalidate_report_cache(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Инвалидация кеша для отчета (для тестирования и администрирования).
    
    Args:
        report_id: ID отчета
        current_user: Текущий пользователь
        db: Сессия БД
        
    Returns:
        Результат инвалидации
    """
    # Проверка прав доступа
    has_access = await ReportService.check_user_has_access_to_report(db, report_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден или нет прав доступа",
        )

    # Удаляем кеш отчета и PDF
    await CacheService.delete(f"reports:user:{current_user.id}:*")
    await CacheService.delete(f"pdf_report:{report_id}")
    
    return {"message": "Кеш успешно инвалидирован"}


@router.get(
    "/{report_id}",
    response_model=AuditReportResponse,
    summary="Информация об отчете",
    description="Получение детальной информации об отчете об аудите",
)
async def get_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditReportResponse:
    """
    Получение детальной информации об отчете.

    Args:
        report_id: ID отчета
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Детальная информация об отчете

    Raises:
        HTTPException: Если отчет не найден или нет прав доступа
    """
    report = await ReportService.get_report_by_id(db, report_id, current_user.id, include_relations=True)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден или нет прав доступа",
        )

    return AuditReportResponse.model_validate(report)


@router.get(
    "/{report_id}/violations",
    response_model=List[ViolationResponse],
    summary="Список нарушений отчета",
    description="Получение списка нарушений конкретного отчета",
)
async def get_report_violations(
    report_id: UUID,
    risk_level: str | None = Query(None, description="Фильтр по уровню риска"),
    order_by: str = Query("risk_level", description="Поле для сортировки"),
    order_direction: str = Query("desc", pattern="^(asc|desc)$", description="Направление сортировки"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ViolationResponse]:
    """
    Получение списка нарушений отчета.

    Args:
        report_id: ID отчета
        risk_level: Фильтр по уровню риска
        order_by: Поле для сортировки
        order_direction: Направление сортировки
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        Список нарушений

    Raises:
        HTTPException: Если отчет не найден или нет прав доступа
    """
    # Проверка прав доступа
    has_access = await ReportService.check_user_has_access_to_report(db, report_id, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден или нет прав доступа",
        )

    filters = ViolationFilterParams(
        risk_level=risk_level,
        order_by=order_by,
        order_direction=order_direction,
    )

    violations = await ReportService.get_violations_by_report(db, report_id, current_user.id, filters)
    return [ViolationResponse.model_validate(v) for v in violations]


@router.get(
    "/{report_id}/export",
    summary="Экспорт отчета в PDF",
    description="Генерация и скачивание PDF-отчета об аудите",
)
async def export_report_pdf(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Генерация PDF-отчета.

    Args:
        report_id: ID отчета
        current_user: Текущий пользователь
        db: Сессия БД

    Returns:
        PDF файл

    Raises:
        HTTPException: Если отчет не найден или нет прав доступа
    """
    # Получаем отчет с полными данными
    report = await ReportService.get_report_by_id(db, report_id, current_user.id, include_relations=True)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден или нет прав доступа",
        )

    # Проверяем, что отчет завершен
    if report.status != AuditReportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отчет еще не завершен. Экспорт доступен только для завершенных отчетов.",
        )

    # Проверяем кеш PDF
    cache_key = f"pdf_report:{report_id}"
    cached_pdf = await CacheService.get(cache_key)
    
    if cached_pdf:
        # PDF в кеше хранится как base64 строка
        import base64
        pdf_content = base64.b64decode(cached_pdf["content"])
        filename = cached_pdf["filename"]
    else:
        try:
            # Генерируем PDF
            pdf_content = await generate_pdf_report(report)

            # Формируем имя файла
            document_name = report.document.original_filename if report.document else "report"
            filename = f"audit_report_{report_id}_{document_name}.pdf"

            # Сохраняем в кеш (24 часа для готовых PDF)
            import base64
            await CacheService.set(
                cache_key,
                {
                    "content": base64.b64encode(pdf_content).decode(),
                    "filename": filename,
                },
                ttl=86400,  # 24 часа
            )
        except Exception as e:
            logger.error("Error generating PDF report", report_id=str(report_id), error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при генерации PDF-отчета",
            )

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

