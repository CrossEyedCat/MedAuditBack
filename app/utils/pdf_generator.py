"""
Утилиты для генерации PDF отчетов.
"""
from io import BytesIO
from datetime import datetime
from typing import List

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from app.models.audit_report import AuditReport
from app.models.violation import Violation, RiskLevel
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_risk_level_color(risk_level: str) -> str:
    """Получение цвета для уровня риска."""
    colors = {
        RiskLevel.CRITICAL.value: "#dc3545",  # Красный
        RiskLevel.HIGH.value: "#fd7e14",  # Оранжевый
        RiskLevel.MEDIUM.value: "#ffc107",  # Желтый
        RiskLevel.LOW.value: "#28a745",  # Зеленый
    }
    return colors.get(risk_level.lower(), "#6c757d")


def _get_risk_level_label(risk_level: str) -> str:
    """Получение метки для уровня риска."""
    labels = {
        RiskLevel.CRITICAL.value: "Критический",
        RiskLevel.HIGH.value: "Высокий",
        RiskLevel.MEDIUM.value: "Средний",
        RiskLevel.LOW.value: "Низкий",
    }
    return labels.get(risk_level.lower(), risk_level)


def _group_violations_by_risk_level(violations: List[Violation]) -> dict:
    """Группировка нарушений по уровню риска."""
    grouped = {
        RiskLevel.CRITICAL.value: [],
        RiskLevel.HIGH.value: [],
        RiskLevel.MEDIUM.value: [],
        RiskLevel.LOW.value: [],
    }

    for violation in violations:
        risk_level = violation.risk_level.value
        if risk_level in grouped:
            grouped[risk_level].append(violation)

    return grouped


async def generate_pdf_report(report: AuditReport) -> bytes:
    """
    Генерация PDF-отчета об аудите.

    Args:
        report: Отчет об аудите с загруженными связями

    Returns:
        Содержимое PDF файла в виде bytes
    """
    # Получаем данные
    violations = report.violations or []
    summary = report.analysis_summary
    document = report.document

    # Группируем нарушения по уровню риска
    violations_by_risk = _group_violations_by_risk_level(violations)

    # Формируем HTML
    html_content = _generate_html_content(report, violations_by_risk, summary, document)

    # Генерируем PDF
    try:
        font_config = FontConfiguration()
        pdf_bytes = HTML(string=html_content).write_pdf(font_config=font_config)
        return pdf_bytes
    except Exception as e:
        logger.error("Error generating PDF", error=str(e))
        raise


def _generate_html_content(
    report: AuditReport,
    violations_by_risk: dict,
    summary,
    document,
) -> str:
    """Генерация HTML содержимого для PDF."""
    # Форматируем даты
    created_at_str = report.created_at.strftime("%d.%m.%Y %H:%M") if report.created_at else "N/A"
    completed_at_str = report.completed_at.strftime("%d.%m.%Y %H:%M") if report.completed_at else "N/A"

    # Статистика по нарушениям
    critical_count = len(violations_by_risk[RiskLevel.CRITICAL.value])
    high_count = len(violations_by_risk[RiskLevel.HIGH.value])
    medium_count = len(violations_by_risk[RiskLevel.MEDIUM.value])
    low_count = len(violations_by_risk[RiskLevel.LOW.value])

    # Генерируем HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Отчет об аудите документа</title>
        <style>
            {_get_css_styles()}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Отчет об аудите медицинской документации</h1>
            <p class="subtitle">MediAudit System</p>
        </div>

        <div class="section">
            <h2>Общая информация</h2>
            <table class="info-table">
                <tr>
                    <td class="label">ID отчета:</td>
                    <td>{report.id}</td>
                </tr>
                <tr>
                    <td class="label">Документ:</td>
                    <td>{document.original_filename if document else 'N/A'}</td>
                </tr>
                <tr>
                    <td class="label">Дата создания:</td>
                    <td>{created_at_str}</td>
                </tr>
                <tr>
                    <td class="label">Дата завершения:</td>
                    <td>{completed_at_str}</td>
                </tr>
                <tr>
                    <td class="label">Статус:</td>
                    <td>{report.status.value}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>Сводка анализа</h2>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{summary.total_risks if summary else 0}</div>
                    <div class="summary-label">Всего рисков</div>
                </div>
                <div class="summary-item critical">
                    <div class="summary-value">{critical_count}</div>
                    <div class="summary-label">Критических</div>
                </div>
                <div class="summary-item high">
                    <div class="summary-value">{high_count}</div>
                    <div class="summary-label">Высоких</div>
                </div>
                <div class="summary-item medium">
                    <div class="summary-value">{medium_count}</div>
                    <div class="summary-label">Средних</div>
                </div>
                <div class="summary-item low">
                    <div class="summary-value">{low_count}</div>
                    <div class="summary-label">Низких</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{summary.compliance_score or 'N/A'}</div>
                    <div class="summary-label">Оценка соответствия</div>
                </div>
            </div>
        </div>
    """

    # Добавляем нарушения по группам
    risk_levels_order = [
        RiskLevel.CRITICAL.value,
        RiskLevel.HIGH.value,
        RiskLevel.MEDIUM.value,
        RiskLevel.LOW.value,
    ]

    for risk_level in risk_levels_order:
        violations = violations_by_risk[risk_level]
        if violations:
            color = _get_risk_level_color(risk_level)
            label = _get_risk_level_label(risk_level)

            html += f"""
            <div class="section">
                <h2 style="color: {color};">Нарушения уровня: {label}</h2>
                <table class="violations-table">
                    <thead>
                        <tr>
                            <th>Код</th>
                            <th>Описание</th>
                            <th>Нормативный документ</th>
                            <th>Контекст</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for violation in violations:
                html += f"""
                        <tr>
                            <td><strong>{violation.code}</strong></td>
                            <td>{violation.description}</td>
                            <td>{violation.regulation_reference or 'N/A'}</td>
                            <td>{violation.context or 'N/A'}</td>
                        </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

    html += """
        <div class="footer">
            <p>Сгенерировано системой MediAudit</p>
            <p>Дата генерации: """ + datetime.utcnow().strftime("%d.%m.%Y %H:%M") + """</p>
        </div>
    </body>
    </html>
    """

    return html


def _get_css_styles() -> str:
    """Получение CSS стилей для PDF."""
    return """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
        }

        .header h1 {
            color: #007bff;
            margin: 0;
            font-size: 24pt;
        }

        .subtitle {
            color: #666;
            margin-top: 5px;
            font-size: 12pt;
        }

        .section {
            margin-bottom: 30px;
            page-break-inside: avoid;
        }

        .section h2 {
            color: #007bff;
            font-size: 16pt;
            margin-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 5px;
        }

        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }

        .info-table td {
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
        }

        .info-table .label {
            font-weight: bold;
            width: 200px;
            color: #555;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }

        .summary-item {
            text-align: center;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            background-color: #f8f9fa;
        }

        .summary-item.critical {
            border-color: #dc3545;
            background-color: #fff5f5;
        }

        .summary-item.high {
            border-color: #fd7e14;
            background-color: #fff8f0;
        }

        .summary-item.medium {
            border-color: #ffc107;
            background-color: #fffef5;
        }

        .summary-item.low {
            border-color: #28a745;
            background-color: #f0fff4;
        }

        .summary-value {
            font-size: 24pt;
            font-weight: bold;
            color: #007bff;
            margin-bottom: 5px;
        }

        .summary-item.critical .summary-value {
            color: #dc3545;
        }

        .summary-item.high .summary-value {
            color: #fd7e14;
        }

        .summary-item.medium .summary-value {
            color: #ffc107;
        }

        .summary-item.low .summary-value {
            color: #28a745;
        }

        .summary-label {
            font-size: 9pt;
            color: #666;
        }

        .violations-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 9pt;
        }

        .violations-table th {
            background-color: #007bff;
            color: white;
            padding: 10px;
            text-align: left;
            font-weight: bold;
        }

        .violations-table td {
            padding: 8px;
            border-bottom: 1px solid #e0e0e0;
        }

        .violations-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 8pt;
        }
    """





