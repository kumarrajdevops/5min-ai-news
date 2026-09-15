from celery import Celery

from app.config import settings

celery_app = Celery(
    "ai_news",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ingestion",
        "app.tasks.dedup",
        "app.tasks.ranking",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)
