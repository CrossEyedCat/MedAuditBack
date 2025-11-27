"""
Endpoints для взаимодействия с NLP-сервисом.
"""
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.nlp import NLPCallbackRequest, NLPCallbackResponse
from app.services.nlp import NLPService
from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.analysis_summary import AnalysisSummary
from app.models.document import DocumentStatus
from app.services.document import DocumentService
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/callback",
    response_model=NLPCallbackResponse,
    summary="Callback от NLP-сервиса",
    description="Endpoint для получения результатов анализа от NLP-сервиса",
)
async def nlp_callback(
    callback_data: NLPCallbackRequest,
    db: AsyncSession = Depends(get_db),
) -> NLPCallbackResponse:
    """
    Обработка callback от NLP-сервиса.

    Args:
        callback_data: Данные callback от NLP-сервиса
        db: Сессия БД

    Returns:
        Подтверждение получения callback

    Raises:
        HTTPException: Если данные невалидны или отчет не найден
    """
    try:
        # Находим отчет по request_id
        from sqlalchemy import select

        result = await db.execute(
            select(AuditReport).where(AuditReport.request_id == callback_data.request_id)
        )
        audit_report = result.scalar_one_or_none()

        if not audit_report:
            logger.warning(
                "Audit report not found for callback",
                request_id=str(callback_data.request_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отчет не найден",
            )

        # Проверяем, что document_id совпадает
        if audit_report.document_id != callback_data.document_id:
            logger.warning(
                "Document ID mismatch in callback",
                request_id=str(callback_data.request_id),
                expected_document_id=str(audit_report.document_id),
                received_document_id=str(callback_data.document_id),
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Несоответствие document_id",
            )

        if callback_data.status == "success":
            # Обработка успешного результата
            await _process_successful_callback(db, audit_report, callback_data)
        else:
            # Обработка ошибки
            await _process_failed_callback(db, audit_report, callback_data)

        logger.info(
            "NLP callback processed",
            request_id=str(callback_data.request_id),
            status=callback_data.status,
        )

        return NLPCallbackResponse(message="Callback успешно обработан")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error processing NLP callback",
            request_id=str(callback_data.request_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обработке callback",
        )


async def _process_successful_callback(
    db: AsyncSession,
    audit_report: AuditReport,
    callback_data: NLPCallbackRequest,
) -> None:
    """Обработка успешного callback."""
    if not callback_data.analysis_result:
        raise ValueError("Отсутствует результат анализа")

    analysis_result = callback_data.analysis_result

    # Сохраняем нарушения
    violations = []
    for violation_data in analysis_result.violations:
        try:
            risk_level = RiskLevel(violation_data.risk_level.lower())
        except ValueError:
            logger.warning(
                "Invalid risk level",
                risk_level=violation_data.risk_level,
            )
            risk_level = RiskLevel.MEDIUM  # Значение по умолчанию

        violation = Violation(
            audit_report_id=audit_report.id,
            code=violation_data.code,
            description=violation_data.description,
            risk_level=risk_level,
            regulation_reference=violation_data.regulation,
            context=violation_data.context,
            offset_start=violation_data.offset_start,
            offset_end=violation_data.offset_end,
        )
        violations.append(violation)

    db.add_all(violations)

    # Сохраняем сводку анализа
    summary_data = analysis_result.summary

    # Подсчитываем количество нарушений по уровням
    high_count = sum(1 for v in violations if v.risk_level == RiskLevel.HIGH)
    medium_count = sum(1 for v in violations if v.risk_level == RiskLevel.MEDIUM)
    low_count = sum(1 for v in violations if v.risk_level == RiskLevel.LOW)

    analysis_summary = AnalysisSummary(
        audit_report_id=audit_report.id,
        total_risks=summary_data.total_risks,
        critical_count=summary_data.critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        compliance_score=summary_data.compliance_score,
    )
    db.add(analysis_summary)

    # Обновляем статус отчета
    audit_report.status = AuditReportStatus.COMPLETED
    audit_report.completed_at = datetime.utcnow()

    # Обновляем статус документа
    await DocumentService.update_document_status(
        db, audit_report.document_id, DocumentStatus.COMPLETED
    )

    await db.commit()

    logger.info(
        "Analysis results saved",
        audit_report_id=str(audit_report.id),
        violations_count=len(violations),
    )


async def _process_failed_callback(
    db: AsyncSession,
    audit_report: AuditReport,
    callback_data: NLPCallbackRequest,
) -> None:
    """Обработка неудачного callback."""
    # Обновляем статус отчета
    audit_report.status = AuditReportStatus.FAILED
    audit_report.error_message = callback_data.error_message or "Ошибка обработки NLP-сервисом"
    audit_report.completed_at = datetime.utcnow()

    # Обновляем статус документа
    await DocumentService.update_document_status(
        db, audit_report.document_id, DocumentStatus.FAILED
    )

    await db.commit()

    logger.warning(
        "Analysis failed",
        audit_report_id=str(audit_report.id),
        error_message=audit_report.error_message,
    )





