"""
Модель нарушения.
"""
from uuid import uuid4

from sqlalchemy import Column, String, Integer, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class RiskLevel(str, enum.Enum):
    """Уровни риска нарушения."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Violation(Base):
    """Модель нарушения."""

    __tablename__ = "violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    audit_report_id = Column(UUID(as_uuid=True), ForeignKey("audit_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    description = Column(String(1000), nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False, index=True)
    regulation_reference = Column(String(500), nullable=True, index=True)
    context = Column(String(2000), nullable=True)
    offset_start = Column(Integer, nullable=True)
    offset_end = Column(Integer, nullable=True)
    
    # Составной индекс для быстрого поиска по отчету и уровню риска
    __table_args__ = (
        {"comment": "Нарушения, выявленные при аудите документа"}
    )

    # Связи
    audit_report = relationship("AuditReport", back_populates="violations")

    def __repr__(self) -> str:
        return f"<Violation(id={self.id}, code={self.code}, risk_level={self.risk_level})>"

