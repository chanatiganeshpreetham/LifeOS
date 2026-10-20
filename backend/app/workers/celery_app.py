from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "lifeos",
    broker=settings.redis_url,
    include=["app.workers.reminder_tasks", "app.workers.finance_tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "deliver-due-reminders": {
            "task": "app.workers.reminder_tasks.dispatch_due_reminders",
            "schedule": 60.0,
        },
        "dispatch-finance-alerts": {
            "task": "app.workers.finance_tasks.dispatch_finance_alerts",
            "schedule": 60.0,
        },
    },
)
