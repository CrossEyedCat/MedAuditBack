"""
Pydantic схемы для взаимодействия с NLP-сервисом.
"""
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field


class NLPRequest(BaseModel):
    """Схема запроса к NLP-сервису."""

    request_id: UUID = Field(..., description="UUID запроса, генерируемый бэкендом")
    document_id: UUID = Field(..., description="UUID документа в БД")
    file_url: str = Field(..., description="URL файла или base64")
    callback_url: str = Field(..., description="URL для callback от NLP-сервиса")


class ViolationItem(BaseModel):
    """Схема нарушения из NLP ответа."""

    code: str = Field(..., description="Код нарушения")
    description: str = Field(..., description="Описание нарушения")
    risk_level: str = Field(..., description="Уровень риска (low, medium, high, critical)")
    regulation: Optional[str] = Field(None, description="Ссылка на нормативный документ")
    context: Optional[str] = Field(None, description="Контекст нарушения в документе")
    offset_start: Optional[int] = Field(None, description="Начало позиции в документе")
    offset_end: Optional[int] = Field(None, description="Конец позиции в документе")


class AnalysisSummaryItem(BaseModel):
    """Схема сводки анализа из NLP ответа."""

    total_risks: int = Field(..., description="Общее количество рисков")
    critical_count: int = Field(default=0, description="Количество критических нарушений")
    compliance_score: Optional[float] = Field(None, description="Оценка соответствия")


class AnalysisResult(BaseModel):
    """Схема результата анализа из NLP ответа."""

    violations: List[ViolationItem] = Field(default_factory=list, description="Список нарушений")
    summary: AnalysisSummaryItem = Field(..., description="Сводка анализа")


class NLPCallbackRequest(BaseModel):
    """Схема callback запроса от NLP-сервиса."""

    request_id: UUID = Field(..., description="UUID запроса")
    document_id: UUID = Field(..., description="UUID документа")
    status: str = Field(..., description="Статус обработки (success или error)")
    analysis_result: Optional[AnalysisResult] = Field(None, description="Результат анализа")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")


class NLPCallbackResponse(BaseModel):
    """Схема ответа на callback от NLP-сервиса."""

    message: str = Field(default="Callback received", description="Сообщение")





