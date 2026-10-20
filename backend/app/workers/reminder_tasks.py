import logging
from uuid import UUID

from app.db.session import SessionLocal
from app.services import reminders as reminder_service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.reminder_tasks.dispatch_due_reminders")
def dispatch_due_reminders() -> int:
    with SessionLocal() as session:
        return reminder_service.deliver_due_reminders(session)


@celery_app.task(name="app.workers.reminder_tasks.deliver_push_notification")
def deliver_push_notification(notification_id: str) -> bool:
    with SessionLocal() as session:
        return reminder_service.send_push_notification(session, UUID(notification_id))
