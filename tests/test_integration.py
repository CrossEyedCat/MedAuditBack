"""
Integration тесты для полного цикла работы системы.
"""
import pytest
import io
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.analysis_summary import AnalysisSummary
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_full_document_processing_cycle(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест полного цикла: регистрация → загрузка документа → генерация отчета → получение результата."""
    # 1. Регистрация пользователя (если нужно)
    # Используем существующего test_user

    # 2. Вход
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    # 3. Загрузка документа
    file_content = b"Test PDF content for audit"
    files = {"file": ("test_document.pdf", io.BytesIO(file_content), "application/pdf")}

    upload_response = await client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {access_token}"},
        files=files,
    )
    assert upload_response.status_code == 201
    document_data = upload_response.json()
    document_id = document_data["id"]

    # 4. Генерация отчета
    generate_response = await client.post(
        "/api/v1/reports/generate",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"document_id": document_id},
    )
    assert generate_response.status_code == 201
    report_data = generate_response.json()
    report_id = report_data["id"]

    # 5. Симуляция callback от NLP (в реальности это делает NLP сервис)
    # Создаем нарушения и сводку вручную
    audit_report = await db_session.get(AuditReport, report_id)
    if audit_report:
        violation = Violation(
            audit_report_id=audit_report.id,
            code="2.13",
            description="Test violation",
            risk_level=RiskLevel.HIGH,
            regulation_reference="Ст. 20 ФЗ-323",
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
        audit_report.status = AuditReportStatus.COMPLETED
        await db_session.commit()

    # 6. Получение отчета
    get_report_response = await client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert get_report_response.status_code == 200
    report = get_report_response.json()
    assert report["status"] == "completed"
    assert len(report.get("violations", [])) >= 1

    # 7. Экспорт PDF
    export_response = await client.get(
        f"/api/v1/reports/{report_id}/export",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_auth_flow(client: AsyncClient, db_session: AsyncSession):
    """Тест полного цикла аутентификации."""
    # 1. Регистрация
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "password123",
        },
    )
    assert register_response.status_code == 201
    tokens = register_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 2. Получение информации о пользователе
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["email"] == "newuser@example.com"

    # 3. Обновление токена
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert "access_token" in new_tokens

    # 4. Выход
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        json={"refresh_token": new_tokens["refresh_token"]},
    )
    assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_nlp_callback_integration(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест интеграции с NLP callback."""
    # Создаем документ и отчет
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

    request_id = uuid4()
    audit_report = AuditReport(
        document_id=document.id,
        request_id=request_id,
        status=AuditReportStatus.PROCESSING,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Отправляем callback от NLP
    callback_data = {
        "request_id": str(request_id),
        "document_id": str(document.id),
        "status": "success",
        "analysis_result": {
            "violations": [
                {
                    "code": "1.1",
                    "description": "Critical violation",
                    "risk_level": "critical",
                    "regulation": "Test regulation",
                    "context": "Test context",
                },
                {
                    "code": "1.2",
                    "description": "High violation",
                    "risk_level": "high",
                },
            ],
            "summary": {
                "total_risks": 200,
                "critical_count": 1,
                "compliance_score": 3.5,
            },
        },
    }

    callback_response = await client.post(
        "/api/v1/nlp/callback",
        json=callback_data,
    )
    assert callback_response.status_code == 200

    # Проверяем, что данные сохранены
    await db_session.refresh(audit_report)
    assert audit_report.status == AuditReportStatus.COMPLETED

    # Проверяем нарушения
    violations = await db_session.execute(
        __import__("sqlalchemy").select(Violation).where(Violation.audit_report_id == audit_report.id)
    )
    violations_list = violations.scalars().all()
    assert len(violations_list) == 2

    # Проверяем сводку
    summary = await db_session.execute(
        __import__("sqlalchemy").select(AnalysisSummary).where(
            AnalysisSummary.audit_report_id == audit_report.id
        )
    )
    summary_obj = summary.scalar_one_or_none()
    assert summary_obj is not None
    assert summary_obj.total_risks == 200
    assert summary_obj.critical_count == 1


@pytest.mark.asyncio
async def test_pdf_generation_integration(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест интеграции генерации PDF."""
    # Создаем полный отчет с нарушениями
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
    violations = [
        Violation(
            audit_report_id=audit_report.id,
            code=f"{i}.{j}",
            description=f"Violation {i}.{j}",
            risk_level=level,
        )
        for i, level in enumerate([RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW], 1)
        for j in range(1, 3)
    ]
    summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=400,
        critical_count=2,
        high_count=2,
        medium_count=2,
        low_count=2,
        compliance_score=3.8,
    )
    db_session.add_all(violations + [summary])
    await db_session.commit()

    # Вход
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )
    access_token = login_response.json()["access_token"]

    # Генерируем PDF
    export_response = await client.get(
        f"/api/v1/reports/{audit_report.id}/export",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/pdf"
    assert len(export_response.content) > 0

    # Проверяем, что PDF содержит ожидаемые данные
    pdf_content = export_response.content
    assert b"PDF" in pdf_content[:10]  # PDF заголовок


