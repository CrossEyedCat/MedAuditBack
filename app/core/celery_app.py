"""
Конфигурация Celery.
"""
from celery import Celery

from app.core.config import settings

# Создание экземпляра Celery
celery_app = Celery(
    "medaudit",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.nlp_tasks"],
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,  # 1 минута
    task_max_retries=3,
)


