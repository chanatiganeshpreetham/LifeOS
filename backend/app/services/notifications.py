import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.reminder import NotificationLog
from app.repositories.reminders import list_active_subscriptions

logger = logging.getLogger(__name__)


def create_user_notification(
    session: Session,
    user_id: UUID,
    notification_type: str,
    payload_summary: str,
    event_key: str,
    reminder_id: UUID | None = None,
    occurrence_at: datetime | None = None,
) -> UUID | None:
    in_app_key = f"{event_key}:in-app"
    if session.scalar(select(NotificationLog.id).where(NotificationLog.event_key == in_app_key)):
        return None

    sent_at = datetime.now(UTC)
    session.add(
        NotificationLog(
            user_id=user_id,
            reminder_id=reminder_id,
            occurrence_at=occurrence_at,
            type=notification_type,
            status="sent",
            event_key=in_app_key,
            payload_summary=payload_summary,
            sent_at=sent_at,
        )
    )
    subscriptions = list_active_subscriptions(session, user_id)
    settings = get_settings()
    if not subscriptions or not (
        settings.vapid_public_key and settings.vapid_private_key and settings.vapid_claims_email
    ):
        if subscriptions:
            logger.warning(
                "Push is not configured; notification %s was delivered in-app only",
                event_key,
            )
        return None

    push_notification = NotificationLog(
        user_id=user_id,
        reminder_id=reminder_id,
        occurrence_at=occurrence_at,
        type="push",
        status="pending",
        event_key=f"{event_key}:push",
        payload_summary=payload_summary,
        sent_at=sent_at,
    )
    session.add(push_notification)
    session.flush()
    return push_notification.id


def enqueue_push_notification(notification_id: UUID) -> None:
    try:
        from app.workers.reminder_tasks import deliver_push_notification

        deliver_push_notification.delay(str(notification_id))
    except Exception:
        logger.exception(
            "Could not enqueue push notification %s; the pending notification will be retried",
            notification_id,
        )
