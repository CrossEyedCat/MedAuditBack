"""
Тесты для API отчетов об аудите.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.document import Document, DocumentStatus
from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.analysis_summary import AnalysisSummary
from app.models.user import User
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_generate_report_success(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест успешного запуска генерации отчета."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
        status=DocumentStatus.PENDING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    # Запускаем генерацию отчета
    response = await client.post(
        "/api/v1/reports/generate",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"document_id": str(document.id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["document_id"] == str(document.id)
    assert data["status"] == "pending"
    assert "Анализ документа запущен" in data["message"]


@pytest.mark.asyncio
async def test_generate_report_document_not_found(client: AsyncClient, test_user: User):
    """Тест генерации отчета для несуществующего документа."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    fake_document_id = uuid4()

    response = await client.post(
        "/api/v1/reports/generate",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"document_id": str(fake_document_id)},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_reports_list(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения списка отчетов."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и отчеты
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    for i in range(3):
        audit_report = AuditReport(
            document_id=document.id,
            request_id=uuid4(),
            status=AuditReportStatus.COMPLETED,
        )
        db_session.add(audit_report)
    await db_session.commit()

    # Получаем список отчетов
    response = await client.get(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 3


@pytest.mark.asyncio
async def test_get_reports_with_filters(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения списка отчетов с фильтрами."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и отчеты с разными статусами
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    report1 = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.COMPLETED,
    )
    report2 = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.FAILED,
    )
    db_session.add_all([report1, report2])
    await db_session.commit()

    # Фильтр по статусу
    response = await client.get(
        "/api/v1/reports/?status=completed",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "completed" for item in data["items"])


@pytest.mark.asyncio
async def test_get_report_by_id(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения отчета по ID."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
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

    # Получаем отчет
    response = await client.get(
        f"/api/v1/reports/{audit_report.id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(audit_report.id)
    assert data["document_id"] == str(document.id)


@pytest.mark.asyncio
async def test_get_report_violations(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения нарушений отчета."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
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

    # Создаем нарушения
    violation1 = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="Test violation 1",
        risk_level=RiskLevel.HIGH,
    )
    violation2 = Violation(
        audit_report_id=audit_report.id,
        code="1.2",
        description="Test violation 2",
        risk_level=RiskLevel.LOW,
    )
    db_session.add_all([violation1, violation2])
    await db_session.commit()

    # Получаем нарушения
    response = await client.get(
        f"/api/v1/reports/{audit_report.id}/violations",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(v["code"] == "1.1" for v in data)


@pytest.mark.asyncio
async def test_get_report_violations_with_filter(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест получения нарушений с фильтром по уровню риска."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
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

    # Создаем нарушения разных уровней
    violation1 = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="High violation",
        risk_level=RiskLevel.HIGH,
    )
    violation2 = Violation(
        audit_report_id=audit_report.id,
        code="1.2",
        description="Low violation",
        risk_level=RiskLevel.LOW,
    )
    db_session.add_all([violation1, violation2])
    await db_session.commit()

    # Фильтр по уровню риска
    response = await client.get(
        f"/api/v1/reports/{audit_report.id}/violations?risk_level=high",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["risk_level"] == "high"


@pytest.mark.asyncio
async def test_export_report_pdf(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест экспорта отчета в PDF."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и завершенный отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
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
    violation = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="Test violation",
        risk_level=RiskLevel.HIGH,
    )
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=100,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
        compliance_score=4.0,
    )
    db_session.add_all([violation, summary])
    await db_session.commit()

    # Экспортируем PDF
    response = await client.get(
        f"/api/v1/reports/{audit_report.id}/export",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_export_report_pdf_not_completed(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест экспорта незавершенного отчета."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем документ и незавершенный отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=1024,
        mime_type="application/pdf",
        file_hash="test_hash",
        status=DocumentStatus.PROCESSING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.PROCESSING,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Пытаемся экспортировать
    response = await client.get(
        f"/api/v1/reports/{audit_report.id}/export",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 400
    assert "не завершен" in response.json()["detail"]





