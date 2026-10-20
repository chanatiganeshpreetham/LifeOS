from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.reminder import NotificationLog, PushSubscription, Reminder


def list_reminders(session: Session, user_id: UUID) -> list[Reminder]:
    return list(
        session.scalars(
            select(Reminder)
            .where(Reminder.user_id == user_id, Reminder.deleted_at.is_(None))
            .order_by(Reminder.is_active.desc(), Reminder.remind_at.asc())
        )
    )


def get_reminder(session: Session, user_id: UUID, reminder_id: UUID) -> Reminder | None:
    return session.scalar(
        select(Reminder).where(
            Reminder.id == reminder_id,
            Reminder.user_id == user_id,
            Reminder.deleted_at.is_(None),
        )
    )


def add_reminder(session: Session, reminder: Reminder) -> None:
    session.add(reminder)


def list_notifications(session: Session, user_id: UUID, limit: int) -> list[NotificationLog]:
    return list(
        session.scalars(
            select(NotificationLog)
            .where(
                NotificationLog.user_id == user_id,
                NotificationLog.type.in_(("in_app", "budget_alert", "cc_due")),
                NotificationLog.status.in_(("sent", "read")),
            )
            .order_by(NotificationLog.sent_at.desc())
            .limit(limit)
        )
    )


def count_unread_notifications(session: Session, user_id: UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(NotificationLog)
            .where(
                NotificationLog.user_id == user_id,
                NotificationLog.type.in_(("in_app", "budget_alert", "cc_due")),
                NotificationLog.status == "sent",
            )
        )
        or 0
    )


def get_notification(
    session: Session, user_id: UUID, notification_id: UUID
) -> NotificationLog | None:
    return session.scalar(
        select(NotificationLog).where(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == user_id,
            NotificationLog.type.in_(("in_app", "budget_alert", "cc_due")),
            NotificationLog.status.in_(("sent", "read")),
        )
    )


def list_active_subscriptions(session: Session, user_id: UUID) -> list[PushSubscription]:
    return list(
        session.scalars(
            select(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.is_active.is_(True),
            )
        )
    )


def get_subscription_by_endpoint(session: Session, endpoint: str) -> PushSubscription | None:
    return session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint).with_for_update()
    )


def add_subscription(session: Session, subscription: PushSubscription) -> None:
    session.add(subscription)


def get_due_reminders(session: Session, now: datetime, limit: int) -> list[Reminder]:
    return list(
        session.scalars(
            select(Reminder)
            .where(
                Reminder.is_active.is_(True),
                Reminder.is_acknowledged.is_(False),
                Reminder.deleted_at.is_(None),
                Reminder.remind_at <= now,
            )
            .order_by(Reminder.remind_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )


def get_push_notification(session: Session, notification_id: UUID) -> NotificationLog | None:
    return session.scalar(
        select(NotificationLog)
        .where(
            NotificationLog.id == notification_id,
            NotificationLog.type == "push",
            NotificationLog.status == "pending",
        )
        .with_for_update(skip_locked=True)
    )


def list_pending_push_notifications(session: Session, limit: int) -> list[NotificationLog]:
    return list(
        session.scalars(
            select(NotificationLog)
            .where(
                NotificationLog.type == "push",
                NotificationLog.status == "pending",
            )
            .order_by(NotificationLog.created_at.asc())
            .limit(limit)
        )
    )
