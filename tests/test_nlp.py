"""
Тесты для интеграции с NLP-сервисом.
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
from app.services.nlp import NLPService
from app.schemas.nlp import NLPCallbackRequest, AnalysisResult, ViolationItem, AnalysisSummaryItem
from app.utils.password import get_password_hash


@pytest.mark.asyncio
async def test_nlp_callback_success(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест успешного callback от NLP-сервиса."""
    # Создаем документ
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=100,
        mime_type="application/pdf",
        file_hash="test_hash",
        status=DocumentStatus.PROCESSING,
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    # Создаем отчет
    request_id = uuid4()
    audit_report = AuditReport(
        document_id=document.id,
        request_id=request_id,
        status=AuditReportStatus.PROCESSING,
    )
    db_session.add(audit_report)
    await db_session.commit()
    await db_session.refresh(audit_report)

    # Формируем callback данные
    callback_data = {
        "request_id": str(request_id),
        "document_id": str(document.id),
        "status": "success",
        "analysis_result": {
            "violations": [
                {
                    "code": "2.13",
                    "description": "Отсутствие информированного согласия",
                    "risk_level": "high",
                    "regulation": "Ст. 20 ФЗ-323",
                    "context": "В разделе отсутствует подпись",
                    "offset_start": 1250,
                    "offset_end": 1300,
                }
            ],
            "summary": {
                "total_risks": 180000,
                "critical_count": 2,
                "compliance_score": 4.0,
            },
        },
    }

    # Отправляем callback
    response = await client.post(
        "/api/v1/nlp/callback",
        json=callback_data,
    )

    assert response.status_code == 200
    assert "успешно обработан" in response.json()["message"]

    # Проверяем, что данные сохранены
    await db_session.refresh(audit_report)
    assert audit_report.status == AuditReportStatus.COMPLETED
    assert audit_report.completed_at is not None

    # Проверяем нарушения
    violations = await db_session.execute(
        __import__("sqlalchemy").select(Violation).where(Violation.audit_report_id == audit_report.id)
    )
    violations_list = violations.scalars().all()
    assert len(violations_list) == 1
    assert violations_list[0].code == "2.13"
    assert violations_list[0].risk_level == RiskLevel.HIGH

    # Проверяем сводку
    summary = await db_session.execute(
        __import__("sqlalchemy").select(AnalysisSummary).where(
            AnalysisSummary.audit_report_id == audit_report.id
        )
    )
    summary_obj = summary.scalar_one_or_none()
    assert summary_obj is not None
    assert summary_obj.total_risks == 180000
    assert summary_obj.critical_count == 2
    assert summary_obj.compliance_score == 4.0


@pytest.mark.asyncio
async def test_nlp_callback_failed(client: AsyncClient, test_user: User, db_session: AsyncSession):
    """Тест неудачного callback от NLP-сервиса."""
    # Создаем документ и отчет
    document = Document(
        user_id=test_user.id,
        original_filename="test.pdf",
        stored_filename="stored_test.pdf",
        file_size=100,
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

    # Формируем callback с ошибкой
    callback_data = {
        "request_id": str(request_id),
        "document_id": str(document.id),
        "status": "error",
        "error_message": "Ошибка обработки документа",
    }

    # Отправляем callback
    response = await client.post(
        "/api/v1/nlp/callback",
        json=callback_data,
    )

    assert response.status_code == 200

    # Проверяем, что статус обновлен
    await db_session.refresh(audit_report)
    assert audit_report.status == AuditReportStatus.FAILED
    assert audit_report.error_message == "Ошибка обработки документа"


@pytest.mark.asyncio
async def test_nlp_callback_not_found(client: AsyncClient):
    """Тест callback с несуществующим request_id."""
    callback_data = {
        "request_id": str(uuid4()),
        "document_id": str(uuid4()),
        "status": "success",
        "analysis_result": {
            "violations": [],
            "summary": {
                "total_risks": 0,
                "critical_count": 0,
                "compliance_score": 0.0,
            },
        },
    }

    response = await client.post(
        "/api/v1/nlp/callback",
        json=callback_data,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_nlp_service_build_file_url():
    """Тест построения URL файла."""
    document_id = uuid4()
    stored_filename = "test_file.pdf"
    url = NLPService.build_file_url(document_id, stored_filename)
    assert str(document_id) in url
    assert "download" in url


@pytest.mark.asyncio
async def test_nlp_service_parse_callback():
    """Тест парсинга callback данных."""
    callback_data = {
        "request_id": str(uuid4()),
        "document_id": str(uuid4()),
        "status": "success",
        "analysis_result": {
            "violations": [
                {
                    "code": "1.1",
                    "description": "Test violation",
                    "risk_level": "low",
                }
            ],
            "summary": {
                "total_risks": 10,
                "critical_count": 1,
                "compliance_score": 5.0,
            },
        },
    }

    parsed = NLPService.parse_callback_data(callback_data)
    assert parsed.status == "success"
    assert parsed.analysis_result is not None
    assert len(parsed.analysis_result.violations) == 1





