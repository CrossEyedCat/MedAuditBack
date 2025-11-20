"""
Модель сводки анализа.
"""
from uuid import uuid4

from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AnalysisSummary(Base):
    """Модель сводки анализа."""

    __tablename__ = "analysis_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_report_id = Column(UUID(as_uuid=True), ForeignKey("audit_reports.id"), unique=True, nullable=False, index=True)
    total_risks = Column(Integer, nullable=False, default=0)
    critical_count = Column(Integer, nullable=False, default=0)
    high_count = Column(Integer, nullable=False, default=0)
    medium_count = Column(Integer, nullable=False, default=0)
    low_count = Column(Integer, nullable=False, default=0)
    compliance_score = Column(Float, nullable=True)

    # Связи
    audit_report = relationship("AuditReport", back_populates="analysis_summary")

    def __repr__(self) -> str:
        return f"<AnalysisSummary(id={self.id}, audit_report_id={self.audit_report_id}, compliance_score={self.compliance_score})>"
