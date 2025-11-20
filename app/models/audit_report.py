"""
Модель отчета об аудите.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AuditReportStatus(str, enum.Enum):
    """Статусы отчета об аудите."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditReport(Base):
    """Модель отчета об аудите."""

    __tablename__ = "audit_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    request_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    status = Column(Enum(AuditReportStatus), default=AuditReportStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    
    # Метаданные анализа (опционально)
    processing_started_at = Column(DateTime, nullable=True)
    processing_duration_seconds = Column(Integer, nullable=True)

    # Связи
    document = relationship("Document", back_populates="audit_reports")
    violations = relationship("Violation", back_populates="audit_report", cascade="all, delete-orphan")
    analysis_summary = relationship("AnalysisSummary", back_populates="audit_report", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AuditReport(id={self.id}, document_id={self.document_id}, status={self.status})>"

