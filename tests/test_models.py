"""
Тесты для моделей базы данных.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import uuid4

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.analysis_summary import AnalysisSummary
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_user_model(db_session: AsyncSession):
    """Тест модели User."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_document_model(db_session: AsyncSession, test_user: User):
    """Тест модели Document."""
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    assert document.id is not None
    assert document.user_id == test_user.id
    assert document.original_filename == "test.pdf"
    assert document.status == DocumentStatus.PENDING
    assert document.created_at is not None


@pytest.mark.asyncio
async def test_audit_report_model(db_session: AsyncSession, test_user: User):
    """Тест модели AuditReport."""
    # Создаем документ
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    # Создаем отчет
    request_id = uuid4()
    audit_report = AuditReport(
        document_id=document.id,
        request_id=request_id,
        status=AuditReportStatus.PENDING,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    assert audit_report.id is not None
    assert audit_report.document_id == document.id
    assert audit_report.request_id == request_id
    assert audit_report.status == AuditReportStatus.PENDING
    assert audit_report.created_at is not None


@pytest.mark.asyncio
async def test_violation_model(db_session: AsyncSession, test_user: User):
    """Тест модели Violation."""
    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.COMPLETED,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Создаем нарушение
    violation = Violation(
        audit_report_id=audit_report.id,
        code="2.13",
        description="Отсутствие информированного согласия",
        risk_level=RiskLevel.HIGH,
        regulation_reference="Ст. 20 ФЗ-323",
        context="В разделе отсутствует подпись",
        offset_start=1250,
        offset_end=1300,
    )
    db_session.add(violation)
    await db_session.commit()
    await db_session.refresh(violation)

    assert violation.id is not None
    assert violation.audit_report_id == audit_report.id
    assert violation.code == "2.13"
    assert violation.risk_level == RiskLevel.HIGH
    assert violation.offset_start == 1250
    assert violation.offset_end == 1300


@pytest.mark.asyncio
async def test_analysis_summary_model(db_session: AsyncSession, test_user: User):
    """Тест модели AnalysisSummary."""
    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.COMPLETED,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Создаем сводку
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=180000,
        critical_count=2,
        high_count=5,
        medium_count=10,
        low_count=20,
        compliance_score=4.0,
    )
    db_session.add(summary)
    await db_session.commit()
    await db_session.refresh(summary)

    assert summary.id is not None
    assert summary.audit_report_id == audit_report.id
    assert summary.total_risks == 180000
    assert summary.critical_count == 2
    assert summary.compliance_score == 4.0


@pytest.mark.asyncio
async def test_cascade_delete_audit_report(db_session: AsyncSession, test_user: User):
    """Тест каскадного удаления при удалении AuditReport."""
    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.COMPLETED,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Создаем нарушения и сводку
    violation1 = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="Test violation 1",
        risk_level=RiskLevel.LOW,
    )
    violation2 = Violation(
        audit_report_id=audit_report.id,
        code="1.2",
        description="Test violation 2",
        risk_level=RiskLevel.MEDIUM,
    )
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=100,
        critical_count=0,
        high_count=0,
        medium_count=1,
        low_count=1,
    )
    db_session.add_all([violation1, violation2, summary])
    await db_session.commit()

    # Удаляем отчет
    await db_session.delete(audit_report)
    await db_session.commit()

    # Проверяем, что нарушения и сводка тоже удалены
    from sqlalchemy import select

    violations_result = await db_session.execute(
        select(Violation).where(Violation.audit_report_id == audit_report.id)
    )
    assert violations_result.scalar_one_or_none() is None

    summary_result = await db_session.execute(
        select(AnalysisSummary).where(AnalysisSummary.audit_report_id == audit_report.id)
    )
    assert summary_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_risk_level_enum():
    """Тест enum RiskLevel."""
    assert RiskLevel.LOW == "low"
    assert RiskLevel.MEDIUM == "medium"
    assert RiskLevel.HIGH == "high"
    assert RiskLevel.CRITICAL == "critical"


@pytest.mark.asyncio
async def test_document_status_enum():
    """Тест enum DocumentStatus."""
    assert DocumentStatus.PENDING == "pending"
    assert DocumentStatus.PROCESSING == "processing"
    assert DocumentStatus.COMPLETED == "completed"
    assert DocumentStatus.FAILED == "failed"


@pytest.mark.asyncio
async def test_audit_report_status_enum():
    """Тест enum AuditReportStatus."""
    assert AuditReportStatus.PENDING == "pending"
    assert AuditReportStatus.PROCESSING == "processing"
    assert AuditReportStatus.COMPLETED == "completed"
    assert AuditReportStatus.FAILED == "failed"


@pytest.mark.asyncio
async def test_relationships(db_session: AsyncSession, test_user: User):
    """Тест связей между моделями."""
    # Создаем документ
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="abc123",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    # Проверяем связь Document -> User
    assert document.user.id == test_user.id

    # Создаем отчет
    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.PENDING,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Проверяем связь AuditReport -> Document
    assert audit_report.document.id == document.id

    # Создаем нарушение
    violation = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="Test",
        risk_level=RiskLevel.LOW,
    )
    db_session.add(violation)
    await db_session.commit()
    await db_session.refresh(violation)

    # Проверяем связь Violation -> AuditReport
    assert violation.audit_report.id == audit_report.id

    # Создаем сводку
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=10,
        critical_count=0,
        high_count=0,
        medium_count=0,
        low_count=1,
    )
    db_session.add(summary)
    await db_session.commit()
    await db_session.refresh(summary)

    # Проверяем связь AnalysisSummary -> AuditReport
    assert summary.audit_report.id == audit_report.id





