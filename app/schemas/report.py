"""
Pydantic схемы для отчетов об аудите.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field


class ViolationResponse(BaseModel):
    """Схема ответа с информацией о нарушении."""

    id: UUID
    code: str
    description: str
    risk_level: str
    regulation_reference: Optional[str] = None
    context: Optional[str] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None

    class Config:
        from_attributes = True


class AnalysisSummaryResponse(BaseModel):
    """Схема ответа со сводкой анализа."""

    id: UUID
    total_risks: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    compliance_score: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentInfoResponse(BaseModel):
    """Схема с информацией о документе в отчете."""

    id: UUID
    original_filename: str
    file_size: int
    mime_type: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditReportBase(BaseModel):
    """Базовая схема отчета."""

    document_id: UUID = Field(..., description="ID документа")


class AuditReportCreate(AuditReportBase):
    """Схема для создания отчета."""

    pass


class AuditReportResponse(BaseModel):
    """Схема ответа с информацией об отчете."""

    id: UUID
    document_id: UUID
    request_id: UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_duration_seconds: Optional[int] = None

    # Связанные данные
    document: Optional[DocumentInfoResponse] = None
    violations: List[ViolationResponse] = Field(default_factory=list)
    analysis_summary: Optional[AnalysisSummaryResponse] = None

    class Config:
        from_attributes = True


class AuditReportListItem(BaseModel):
    """Схема элемента списка отчетов."""

    id: UUID
    document_id: UUID
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    compliance_score: Optional[float] = None
    violations_count: int = 0
    document_filename: Optional[str] = None

    class Config:
        from_attributes = True


class AuditReportListResponse(BaseModel):
    """Схема ответа со списком отчетов."""

    items: List[AuditReportListItem] = Field(..., description="Список отчетов")
    total: int = Field(..., description="Общее количество отчетов")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")


class ReportGenerateRequest(BaseModel):
    """Схема запроса на генерацию отчета."""

    document_id: UUID = Field(..., description="ID документа для анализа")


class ReportGenerateResponse(BaseModel):
    """Схема ответа после запуска генерации отчета."""

    id: UUID
    document_id: UUID
    status: str
    message: str = Field(default="Анализ документа запущен", description="Сообщение")


class ReportFilterParams(BaseModel):
    """Параметры фильтрации отчетов."""

    status: Optional[str] = Field(None, description="Фильтр по статусу")
    document_id: Optional[UUID] = Field(None, description="Фильтр по ID документа")
    risk_level: Optional[str] = Field(None, description="Фильтр по уровню риска нарушений")
    date_from: Optional[datetime] = Field(None, description="Фильтр по дате создания (от)")
    date_to: Optional[datetime] = Field(None, description="Фильтр по дате создания (до)")
    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(default=20, ge=1, le=100, description="Размер страницы")
    order_by: Optional[str] = Field(default="created_at", description="Поле для сортировки")
    order_direction: str = Field(default="desc", pattern="^(asc|desc)$", description="Направление сортировки")
    include_violations: bool = Field(default=False, description="Включить нарушения в ответ")
    include_summary: bool = Field(default=True, description="Включить сводку в ответ")


class ViolationFilterParams(BaseModel):
    """Параметры фильтрации нарушений."""

    risk_level: Optional[str] = Field(None, description="Фильтр по уровню риска")
    order_by: Optional[str] = Field(default="risk_level", description="Поле для сортировки")
    order_direction: str = Field(default="desc", pattern="^(asc|desc)$", description="Направление сортировки")





