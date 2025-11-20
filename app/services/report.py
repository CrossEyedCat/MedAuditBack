"""
Сервис для работы с отчетами об аудите.
"""
from uuid import UUID
from typing import Optional, List, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload, joinedload

from app.models.audit_report import AuditReport, AuditReportStatus
from app.models.violation import Violation, RiskLevel
from app.models.analysis_summary import AnalysisSummary
from app.models.document import Document
from app.schemas.report import ReportFilterParams, ViolationFilterParams
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportService:
    """Сервис для работы с отчетами об аудите."""

    @staticmethod
    async def create_audit_report(
        db: AsyncSession,
        document_id: UUID,
        request_id: UUID,
    ) -> AuditReport:
        """
        Создание отчета об аудите.

        Args:
            db: Сессия БД
            document_id: ID документа
            request_id: ID запроса к NLP

        Returns:
            Созданный отчет
        """
        audit_report = AuditReport(
            document_id=document_id,
            request_id=request_id,
            status=AuditReportStatus.PENDING,
        )

        db.add(audit_report)
        await db.commit()
        await db.refresh(audit_report)
        logger.info("Audit report created", audit_report_id=str(audit_report.id), document_id=str(document_id))
        return audit_report

    @staticmethod
    async def get_report_by_id(
        db: AsyncSession,
        report_id: UUID,
        user_id: Optional[UUID] = None,
        include_relations: bool = True,
    ) -> Optional[AuditReport]:
        """
        Получение отчета по ID.

        Args:
            db: Сессия БД
            report_id: ID отчета
            user_id: ID пользователя (для проверки прав доступа)
            include_relations: Включить связанные данные

        Returns:
            Отчет или None
        """
        query = select(AuditReport).where(AuditReport.id == report_id)

        if include_relations:
            query = query.options(
                selectinload(AuditReport.violations),
                selectinload(AuditReport.analysis_summary),
                joinedload(AuditReport.document),
            )

        if user_id:
            # Проверка через связь с документом
            query = query.join(Document).where(Document.user_id == user_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_reports_by_user(
        db: AsyncSession,
        user_id: UUID,
        filters: ReportFilterParams,
    ) -> Tuple[List[AuditReport], int]:
        """
        Получение списка отчетов пользователя с фильтрацией и пагинацией.

        Args:
            db: Сессия БД
            user_id: ID пользователя
            filters: Параметры фильтрации

        Returns:
            Кортеж (список отчетов, общее количество)
        """
        # Базовый запрос с join к документам
        query = (
            select(AuditReport)
            .join(Document)
            .where(Document.user_id == user_id)
        )

        count_query = (
            select(func.count(AuditReport.id))
            .join(Document)
            .where(Document.user_id == user_id)
        )

        # Применение фильтров
        if filters.status:
            try:
                status_enum = AuditReportStatus(filters.status)
                query = query.where(AuditReport.status == status_enum)
                count_query = count_query.where(AuditReport.status == status_enum)
            except ValueError:
                pass

        if filters.document_id:
            query = query.where(AuditReport.document_id == filters.document_id)
            count_query = count_query.where(AuditReport.document_id == filters.document_id)

        if filters.date_from:
            query = query.where(AuditReport.created_at >= filters.date_from)
            count_query = count_query.where(AuditReport.created_at >= filters.date_from)

        if filters.date_to:
            query = query.where(AuditReport.created_at <= filters.date_to)
            count_query = count_query.where(AuditReport.created_at <= filters.date_to)

        # Фильтр по уровню риска нарушений
        if filters.risk_level:
            try:
                risk_level_enum = RiskLevel(filters.risk_level.lower())
                # Подзапрос для отчетов с нарушениями нужного уровня
                violations_subquery = (
                    select(Violation.audit_report_id)
                    .where(Violation.risk_level == risk_level_enum)
                    .distinct()
                )
                query = query.where(AuditReport.id.in_(violations_subquery))
                count_query = count_query.where(AuditReport.id.in_(violations_subquery))
            except ValueError:
                pass

        # Подсчет общего количества (оптимизированный запрос)
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Включение связанных данных
        if filters.include_summary:
            query = query.options(selectinload(AuditReport.analysis_summary))

        if filters.include_violations:
            query = query.options(selectinload(AuditReport.violations))

        query = query.options(joinedload(AuditReport.document))

        # Сортировка
        order_column = getattr(AuditReport, filters.order_by, AuditReport.created_at)
        if filters.order_by == "compliance_score":
            # Сортировка по compliance_score через analysis_summary
            query = query.outerjoin(AnalysisSummary).order_by(
                desc(AnalysisSummary.compliance_score) if filters.order_direction == "desc"
                else asc(AnalysisSummary.compliance_score)
            )
        else:
            if filters.order_direction == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        # Пагинация
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Выполнение запроса
        result = await db.execute(query)
        reports = result.unique().scalars().all()

        return list(reports), total

    @staticmethod
    async def get_violations_by_report(
        db: AsyncSession,
        report_id: UUID,
        user_id: Optional[UUID] = None,
        filters: Optional[ViolationFilterParams] = None,
    ) -> List[Violation]:
        """
        Получение нарушений отчета.

        Args:
            db: Сессия БД
            report_id: ID отчета
            user_id: ID пользователя (для проверки прав доступа)
            filters: Параметры фильтрации

        Returns:
            Список нарушений
        """
        query = select(Violation).where(Violation.audit_report_id == report_id)

        if user_id:
            # Проверка прав доступа через связь с отчетом и документом
            query = (
                query.join(AuditReport)
                .join(Document)
                .where(Document.user_id == user_id)
            )

        if filters:
            if filters.risk_level:
                try:
                    risk_level_enum = RiskLevel(filters.risk_level.lower())
                    query = query.where(Violation.risk_level == risk_level_enum)
                except ValueError:
                    pass

            # Сортировка
            order_column = getattr(Violation, filters.order_by, Violation.risk_level)
            if filters.order_direction == "desc":
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def check_user_has_access_to_report(
        db: AsyncSession,
        report_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Проверка прав доступа пользователя к отчету.

        Args:
            db: Сессия БД
            report_id: ID отчета
            user_id: ID пользователя

        Returns:
            True если есть доступ, иначе False
        """
        result = await db.execute(
            select(AuditReport)
            .join(Document)
            .where(
                and_(
                    AuditReport.id == report_id,
                    Document.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none() is not None

