"""
Нагрузочное тестирование ключевых endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import time

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_load_document_upload(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Нагрузочный тест загрузки документов."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    async def upload_document(i: int):
        """Вспомогательная функция для загрузки документа."""
        import io
        file_content = f"Test content {i}".encode()
        files = {"file": (f"test{i}.pdf", io.BytesIO(file_content), "application/pdf")}
        response = await client.post(
            "/api/v1/documents/upload",
            headers={"Authorization": f"Bearer {access_token}"},
            files=files,
        )
        return response.status_code == 201

    # Загружаем 10 документов параллельно
    start_time = time.time()
    tasks = [upload_document(i) for i in range(10)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()

    successful_uploads = sum(results)
    assert successful_uploads >= 8  # Допускаем некоторые ошибки при нагрузке
    assert (end_time - start_time) < 30  # Все должно завершиться за 30 секунд


@pytest.mark.asyncio
async def test_load_reports_list(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Нагрузочный тест получения списка отчетов."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем много отчетов
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

    from app.models.audit_report import AuditReport, AuditReportStatus
    from uuid import uuid4

    reports = [
        AuditReport(
            document_id=document.id,
            request_id=uuid4(),
            status=AuditReportStatus.COMPLETED,
        )
        for _ in range(50)
    ]
    db_session.add_all(reports)
    await db_session.commit()

    async def get_reports_page(page: int):
        """Вспомогательная функция для получения страницы отчетов."""
        response = await client.get(
            f"/api/v1/reports/?page={page}&page_size=20",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return response.status_code == 200

    # Получаем несколько страниц параллельно
    start_time = time.time()
    tasks = [get_reports_page(i) for i in range(1, 4)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()

    assert all(results)
    assert (end_time - start_time) < 5  # Должно быть быстро


@pytest.mark.asyncio
async def test_load_pdf_generation(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Нагрузочный тест генерации PDF."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Создаем отчет с данными
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

    from app.models.audit_report import AuditReport, AuditReportStatus
    from app.models.violation import Violation, RiskLevel
    from app.models.analysis_summary import AnalysisSummary
    from uuid import uuid4

    audit_report = AuditReport(
        document_id=document.id,
        request_id=uuid4(),
        status=AuditReportStatus.COMPLETED,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Добавляем данные
    violation = Violation(
        audit_report_id=audit_report.id,
        code="1.1",
        description="Test",
        risk_level=RiskLevel.HIGH,
    )
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=100,
        critical_count=0,
        high_count=1,
        medium_count=0,
        low_count=0,
    )
    db_session.add_all([violation, summary])
    await db_session.commit()

    async def generate_pdf():
        """Вспомогательная функция для генерации PDF."""
        response = await client.get(
            f"/api/v1/reports/{audit_report.id}/export",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return response.status_code == 200 and len(response.content) > 0

    # Генерируем несколько PDF параллельно
    start_time = time.time()
    tasks = [generate_pdf() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    end_time = time.time()

    assert all(results)
    assert (end_time - start_time) < 30  # Генерация PDF может быть медленной





