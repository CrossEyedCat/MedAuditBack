"""
Метрики Prometheus для мониторинга приложения.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import prometheus_client

# Метрики HTTP запросов
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Метрики базы данных
db_queries_total = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['query_type']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)

# Метрики Redis
redis_operations_total = Counter(
    'redis_operations_total',
    'Total number of Redis operations',
    ['operation']
)

redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation duration in seconds',
    ['operation']
)

# Метрики Celery задач
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total number of Celery tasks',
    ['task_name', 'status']
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name']
)

# Метрики документов
documents_uploaded_total = Counter(
    'documents_uploaded_total',
    'Total number of uploaded documents',
    ['file_type']
)

documents_processed_total = Counter(
    'documents_processed_total',
    'Total number of processed documents',
    ['status']
)

# Метрики отчетов
reports_generated_total = Counter(
    'reports_generated_total',
    'Total number of generated reports',
    ['status']
)

violations_detected_total = Counter(
    'violations_detected_total',
    'Total number of detected violations',
    ['risk_level']
)

# Метрики активных подключений
active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    ['connection_type']
)

# Метрики размера очереди
queue_size = Gauge(
    'queue_size',
    'Size of the task queue',
    ['queue_name']
)


def get_metrics_response() -> Response:
    """Возвращает метрики в формате Prometheus."""
    try:
        output = generate_latest(prometheus_client.REGISTRY)
        # Убеждаемся, что ответ заканчивается новой строкой
        if isinstance(output, bytes):
            output = output.decode('utf-8')
        if not output.endswith('\n'):
            output += '\n'
        return Response(
            content=output,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        # Fallback на простой формат
        from prometheus_client import generate_latest as gl
        output = gl()
        return Response(
            content=output,
            media_type=CONTENT_TYPE_LATEST
        )

