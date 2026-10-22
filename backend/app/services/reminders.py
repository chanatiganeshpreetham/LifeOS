import calendar
import json
import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from requests import RequestException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User
from app.models.reminder import NotificationLog, PushSubscription, Reminder
from app.repositories import reminders as reminder_repository
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.services.notifications import create_user_notification

logger = logging.getLogger(__name__)
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
_PUSH_BATCH_SIZE = 100


def _now() -> datetime:
    return datetime.now(UTC)


def _timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your profile timezone is invalid. Update it before scheduling reminders.",
        ) from None


def _get_owned_reminder(session: Session, user: User, reminder_id: UUID) -> Reminder:
    reminder = reminder_repository.get_reminder(session, user.id, reminder_id)
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    return reminder


def list_reminders(session: Session, user: User) -> list[Reminder]:
    return reminder_repository.list_reminders(session, user.id)


def dashboard_reminders(session: Session, user: User) -> list[Reminder]:
    timezone = _timezone(user)
    now = _now()
    local_today = now.astimezone(timezone).date()
    horizon = datetime.combine(local_today + timedelta(days=8), time.min, tzinfo=timezone)
    return list(
        session.scalars(
            select(Reminder)
            .where(
                Reminder.user_id == user.id,
                Reminder.is_active.is_(True),
                Reminder.deleted_at.is_(None),
                Reminder.remind_at >= now,
                Reminder.remind_at < horizon.astimezone(UTC),
            )
            .order_by(Reminder.remind_at)
            .limit(4)
        )
    )


def create_reminder(session: Session, user: User, payload: ReminderCreate) -> Reminder:
    timezone = _timezone(user)
    remind_at = payload.remind_at.astimezone(UTC)
    reminder = Reminder(
        user_id=user.id,
        title=payload.title,
        notes=payload.notes,
        remind_at=remind_at,
        is_recurring=payload.is_recurring,
        frequency=payload.frequency,
        interval_days=payload.interval_days,
        day_of_month=remind_at.astimezone(timezone).day if payload.frequency == "monthly" else None,
        weekdays=list(payload.weekdays) if payload.weekdays else None,
    )
    reminder_repository.add_reminder(session, reminder)
    session.commit()
    session.refresh(reminder)
    return reminder


def update_reminder(
    session: Session,
    user: User,
    reminder_id: UUID,
    payload: ReminderUpdate,
) -> Reminder:
    _timezone(user)
    reminder = _get_owned_reminder(session, user, reminder_id)
    changes = payload.model_dump(exclude_unset=True)
    for key in ("title", "remind_at", "is_recurring", "is_active"):
        if key in changes and changes[key] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{key} cannot be null.",
            )
    next_recurring = changes.get("is_recurring", reminder.is_recurring)
    next_frequency = changes.get("frequency", reminder.frequency)
    next_interval = changes.get("interval_days", reminder.interval_days)
    previous_frequency = reminder.frequency
    if next_recurring != (next_frequency is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a recurrence frequency for recurring reminders only.",
        )
    if (next_frequency == "custom") != (next_interval is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Custom recurrence requires an interval of 1 to 365 days.",
        )
    next_weekdays = changes.get("weekdays", reminder.weekdays)
    if next_frequency != "weekly" and next_weekdays:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Weekdays can only be used for weekly reminders.",
        )
    if next_frequency == "weekly" and next_weekdays is not None and not next_weekdays:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose at least one weekday.",
        )

    if "remind_at" in changes and changes["remind_at"] is not None:
        changes["remind_at"] = changes["remind_at"].astimezone(UTC)
        reminder.is_acknowledged = False
    for key, value in changes.items():
        setattr(reminder, key, value)
    if "is_recurring" in changes and not changes["is_recurring"]:
        reminder.frequency = None
        reminder.interval_days = None
        reminder.weekdays = None
    if changes.get("is_active") is True:
        reminder.is_acknowledged = False
    if reminder.frequency != "custom":
        reminder.interval_days = None
    if reminder.frequency != "weekly":
        reminder.weekdays = None
    if reminder.frequency != "monthly":
        reminder.day_of_month = None
    elif "remind_at" in changes or ("frequency" in changes and previous_frequency != "monthly"):
        reminder.day_of_month = reminder.remind_at.astimezone(_timezone(user)).day
    session.commit()
    session.refresh(reminder)
    return reminder


def acknowledge_reminder(session: Session, user: User, reminder_id: UUID) -> Reminder:
    reminder = _get_owned_reminder(session, user, reminder_id)
    reminder.is_acknowledged = True
    reminder.is_active = False
    session.commit()
    session.refresh(reminder)
    return reminder


def delete_reminder(session: Session, user: User, reminder_id: UUID) -> None:
    reminder = _get_owned_reminder(session, user, reminder_id)
    reminder.deleted_at = _now()
    reminder.is_active = False
    session.commit()


def get_notifications(
    session: Session, user: User, limit: int = 30
) -> tuple[list[NotificationLog], int]:
    return (
        reminder_repository.list_notifications(session, user.id, limit),
        reminder_repository.count_unread_notifications(session, user.id),
    )


def mark_notification_read(session: Session, user: User, notification_id: UUID) -> NotificationLog:
    notification = reminder_repository.get_notification(session, user.id, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )
    if notification.status == "sent":
        notification.status = "read"
        notification.read_at = _now()
        session.commit()
    return notification


def mark_all_notifications_read(session: Session, user: User) -> None:
    now = _now()
    session.execute(
        update(NotificationLog)
        .where(
            NotificationLog.user_id == user.id,
            NotificationLog.type.in_(("in_app", "budget_alert", "cc_due")),
            NotificationLog.status == "sent",
        )
        .values(status="read", read_at=now)
    )
    session.commit()


def get_push_config() -> tuple[bool, str | None]:
    settings = get_settings()
    enabled = bool(
        settings.vapid_public_key and settings.vapid_private_key and settings.vapid_claims_email
    )
    return enabled, settings.vapid_public_key if enabled else None


def upsert_push_subscription(
    session: Session,
    user: User,
    endpoint: str,
    p256dh_key: str,
    auth_key: str,
    device_label: str | None,
) -> None:
    enabled, _ = get_push_config()
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Browser push is not configured on this server. In-app reminders remain available."
            ),
        )
    subscription = reminder_repository.get_subscription_by_endpoint(session, endpoint)
    if subscription is None:
        subscription = PushSubscription(
            user_id=user.id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            device_label=device_label,
        )
        reminder_repository.add_subscription(session, subscription)
    else:
        subscription.user_id = user.id
        subscription.p256dh_key = p256dh_key
        subscription.auth_key = auth_key
        subscription.device_label = device_label
        subscription.is_active = True
    session.commit()


def remove_push_subscription(session: Session, user: User, endpoint: str) -> None:
    subscription = reminder_repository.get_subscription_by_endpoint(session, endpoint)
    if subscription is None or subscription.user_id != user.id:
        return
    subscription.is_active = False
    session.commit()


def _local_datetime(day: date, source: datetime, timezone: ZoneInfo) -> datetime:
    local_source = source.astimezone(timezone)
    candidate = datetime.combine(day, local_source.timetz().replace(tzinfo=None), tzinfo=timezone)
    round_trip = candidate.astimezone(UTC).astimezone(timezone)
    if round_trip.replace(tzinfo=None) != candidate.replace(tzinfo=None):
        return round_trip
    return candidate


def next_occurrence(
    reminder: Reminder, timezone: ZoneInfo, occurrence_at: datetime | None = None
) -> datetime:
    local_due = (occurrence_at or reminder.remind_at).astimezone(timezone)
    due_day = local_due.date()
    if reminder.frequency == "daily":
        next_day = due_day + timedelta(days=1)
    elif reminder.frequency == "custom":
        next_day = due_day + timedelta(days=reminder.interval_days or 1)
    elif reminder.frequency == "weekly":
        weekdays = reminder.weekdays or [_WEEKDAYS[due_day.weekday()]]
        candidates = sorted(_WEEKDAYS.index(day) for day in weekdays)
        days_until = next(
            (weekday - due_day.weekday() for weekday in candidates if weekday > due_day.weekday()),
            7 - due_day.weekday() + candidates[0],
        )
        next_day = due_day + timedelta(days=days_until)
    elif reminder.frequency == "monthly":
        year = due_day.year + (1 if due_day.month == 12 else 0)
        month = 1 if due_day.month == 12 else due_day.month + 1
        anchor_day = reminder.day_of_month or due_day.day
        next_day = date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))
    else:
        raise ValueError(f"Unexpected reminder recurrence frequency: {reminder.frequency}")
    return _local_datetime(next_day, reminder.remind_at, timezone).astimezone(UTC)


def occurrences_between(
    reminder: Reminder,
    start_at: datetime,
    end_at: datetime,
    timezone: ZoneInfo,
) -> list[datetime]:
    if not reminder.is_recurring:
        return [reminder.remind_at] if start_at <= reminder.remind_at < end_at else []

    original = reminder.remind_at
    due_day = original.astimezone(timezone).date()
    start_day = start_at.astimezone(timezone).date()
    if original >= start_at:
        occurrence = original
    elif reminder.frequency in ("daily", "custom"):
        interval = 1 if reminder.frequency == "daily" else reminder.interval_days or 1
        elapsed = max(0, (start_day - due_day).days)
        steps = elapsed // interval
        candidate_day = due_day + timedelta(days=steps * interval)
        occurrence = _local_datetime(candidate_day, original, timezone).astimezone(UTC)
        while occurrence < start_at:
            occurrence = next_occurrence(reminder, timezone, occurrence)
    elif reminder.frequency == "weekly":
        weekdays = reminder.weekdays or [_WEEKDAYS[due_day.weekday()]]
        selected = {_WEEKDAYS.index(day) for day in weekdays}
        candidate_day = max(start_day, due_day + timedelta(days=1))
        occurrence = _local_datetime(candidate_day, original, timezone).astimezone(UTC)
        for _ in range(15):
            if candidate_day.weekday() in selected and occurrence >= start_at:
                break
            candidate_day += timedelta(days=1)
            occurrence = _local_datetime(candidate_day, original, timezone).astimezone(UTC)
        else:
            return []
    elif reminder.frequency == "monthly":
        anchor_day = reminder.day_of_month or due_day.day
        month_offset = (start_day.year - due_day.year) * 12 + start_day.month - due_day.month
        month_offset = max(0, month_offset)
        year = due_day.year + (due_day.month - 1 + month_offset) // 12
        month = (due_day.month - 1 + month_offset) % 12 + 1
        candidate_day = date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))
        occurrence = _local_datetime(candidate_day, original, timezone).astimezone(UTC)
        if candidate_day <= due_day and occurrence < start_at:
            occurrence = next_occurrence(reminder, timezone, occurrence)
        while occurrence < start_at:
            occurrence = next_occurrence(reminder, timezone, occurrence)
    else:
        raise ValueError(f"Unexpected reminder recurrence frequency: {reminder.frequency}")

    occurrences: list[datetime] = []
    while occurrence < end_at:
        if occurrence >= start_at:
            occurrences.append(occurrence)
        occurrence = next_occurrence(reminder, timezone, occurrence)
    return occurrences


def next_future_occurrence(reminder: Reminder, timezone: ZoneInfo, now: datetime) -> datetime:
    local_due = reminder.remind_at.astimezone(timezone)
    local_now = now.astimezone(timezone)
    due_day = local_due.date()

    if reminder.frequency in ("daily", "custom"):
        interval = 1 if reminder.frequency == "daily" else reminder.interval_days or 1
        elapsed_days = (local_now.date() - due_day).days
        intervals = max(1, elapsed_days // interval + 1)
        next_day = due_day + timedelta(days=interval * intervals)
        return _local_datetime(next_day, reminder.remind_at, timezone).astimezone(UTC)

    if reminder.frequency == "weekly":
        selected_weekdays = set(reminder.weekdays or [_WEEKDAYS[due_day.weekday()]])
        for offset in range(0, 8):
            candidate_day = local_now.date() + timedelta(days=offset)
            if candidate_day > due_day and _WEEKDAYS[candidate_day.weekday()] in selected_weekdays:
                candidate = _local_datetime(candidate_day, reminder.remind_at, timezone)
                if candidate > local_now:
                    return candidate.astimezone(UTC)
        raise ValueError(f"Could not compute next weekly reminder for {reminder.id}")

    if reminder.frequency == "monthly":
        anchor_day = reminder.day_of_month or due_day.day
        month_delta = max(
            1,
            (local_now.year - due_day.year) * 12 + local_now.month - due_day.month,
        )
        for offset in range(month_delta, month_delta + 2):
            month_index = due_day.month - 1 + offset
            year = due_day.year + month_index // 12
            month = month_index % 12 + 1
            candidate_day = date(
                year,
                month,
                min(anchor_day, calendar.monthrange(year, month)[1]),
            )
            candidate = _local_datetime(candidate_day, reminder.remind_at, timezone)
            if candidate > local_now:
                return candidate.astimezone(UTC)
        raise ValueError(f"Could not compute next monthly reminder for {reminder.id}")

    raise ValueError(f"Unexpected reminder recurrence frequency: {reminder.frequency}")


def deliver_due_reminders(session: Session) -> int:
    now = _now()
    reminders = reminder_repository.get_due_reminders(session, now, limit=100)
    push_ids: list[UUID] = []
    processed = 0
    for reminder in reminders:
        user = session.get(User, reminder.user_id)
        if user is None or not user.is_active:
            reminder.is_active = False
            continue
        try:
            timezone = _timezone(user)
        except HTTPException as error:
            reminder.is_active = False
            logger.error(
                "Disabled reminder %s because its owner has an invalid timezone: %s",
                reminder.id,
                error.detail,
            )
            continue
        occurrence_at = reminder.remind_at
        notification_id = create_user_notification(
            session,
            user.id,
            "in_app",
            reminder.title,
            f"reminder:{reminder.id}:{occurrence_at.isoformat()}",
            reminder_id=reminder.id,
            occurrence_at=occurrence_at,
        )
        if notification_id:
            push_ids.append(notification_id)

        if reminder.is_recurring:
            reminder.remind_at = next_future_occurrence(reminder, timezone, now)
            reminder.is_acknowledged = False
        else:
            reminder.is_active = False
        processed += 1

    push_ids.extend(
        notification.id
        for notification in reminder_repository.list_pending_push_notifications(
            session, limit=_PUSH_BATCH_SIZE
        )
        if notification.id not in push_ids
    )
    session.commit()
    for notification_id in push_ids:
        try:
            send_push_notification(session, notification_id)
        except Exception:
            logger.exception("Could not deliver push notification %s", notification_id)
    return processed


def send_push_notification(session: Session, notification_id: UUID) -> bool:
    settings = get_settings()
    notification = reminder_repository.get_push_notification(session, notification_id)
    if notification is None:
        return False

    subscriptions = reminder_repository.list_active_subscriptions(session, notification.user_id)
    if not subscriptions:
        notification.status = "failed"
        notification.payload_summary = "No active browser push subscriptions."
        session.commit()
        logger.warning("No active push subscriptions for notification %s", notification.id)
        return False

    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush

    vapid_private_key = settings.vapid_private_key
    if not settings.vapid_public_key or not vapid_private_key or not settings.vapid_claims_email:
        logger.error("VAPID settings are missing for push notification %s", notification.id)
        notification.status = "failed"
        notification.payload_summary = "Browser push is not configured."
        session.commit()
        return False
    vapid = Vapid.from_string(vapid_private_key.get_secret_value())

    success_count = 0
    errors: list[str] = []
    for subscription in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                },
                data=json.dumps(
                    {
                        "title": "LifeOS reminder",
                        "body": notification.payload_summary or "A reminder is due.",
                        "url": "/reminders",
                    }
                ),
                vapid_private_key=vapid,
                vapid_claims={"sub": f"mailto:{settings.vapid_claims_email}"},
                timeout=10,
            )
            success_count += 1
        except WebPushException as error:
            response_status = error.response.status_code if error.response else None
            if response_status in (404, 410):
                subscription.is_active = False
            error_line = f"Push delivery failed with status {response_status}."
            errors.append(error_line)
            logger.exception("Push delivery failed for subscription %s", subscription.id)
        except RequestException:
            errors.append("Push delivery failed unexpectedly.")
            logger.exception(
                "Unexpected push delivery failure for subscription %s", subscription.id
            )

    if errors:
        notification.payload_summary = "; ".join(errors[:3])
        notification.status = "failed" if success_count == 0 else "sent"
    elif success_count:
        notification.status = "sent"
    else:
        notification.status = "failed"
        notification.payload_summary = "Push delivery did not reach an active device."
    session.commit()
    return success_count > 0
