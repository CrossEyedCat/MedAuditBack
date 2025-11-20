"""
Pydantic схемы для документов.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional, List

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Базовая схема документа."""

    original_filename: str = Field(..., description="Оригинальное имя файла")


class DocumentCreate(DocumentBase):
    """Схема для создания документа (используется внутренне)."""

    stored_filename: str
    file_size: int
    mime_type: str
    file_hash: str


class DocumentResponse(DocumentBase):
    """Схема ответа с информацией о документе."""

    id: UUID
    user_id: UUID
    stored_filename: str
    file_size: int
    mime_type: str
    file_hash: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Схема ответа со списком документов."""

    items: List[DocumentResponse] = Field(..., description="Список документов")
    total: int = Field(..., description="Общее количество документов")
    page: int = Field(..., description="Текущая страница")
    page_size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")


class DocumentUploadResponse(DocumentResponse):
    """Схема ответа после загрузки документа."""

    message: str = Field(default="Документ успешно загружен", description="Сообщение")


class DocumentFilterParams(BaseModel):
    """Параметры фильтрации документов."""

    status: Optional[str] = Field(None, description="Фильтр по статусу")
    mime_type: Optional[str] = Field(None, description="Фильтр по типу файла")
    page: int = Field(default=1, ge=1, description="Номер страницы")
    page_size: int = Field(default=20, ge=1, le=100, description="Размер страницы")
    order_by: Optional[str] = Field(default="created_at", description="Поле для сортировки")
    order_direction: str = Field(default="desc", pattern="^(asc|desc)$", description="Направление сортировки")


