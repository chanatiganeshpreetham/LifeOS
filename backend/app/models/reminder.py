from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.db.base import Base


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (
        CheckConstraint(
            "frequency IS NULL OR frequency IN ('daily', 'weekly', 'monthly', 'custom')",
            name="ck_reminders_frequency",
        ),
        CheckConstraint(
            "(is_recurring AND frequency IS NOT NULL) OR (NOT is_recurring AND frequency IS NULL)",
            name="ck_reminders_recurring_frequency",
        ),
        CheckConstraint(
            "frequency != 'custom' OR "
            "(interval_days IS NOT NULL AND interval_days BETWEEN 1 AND 365)",
            name="ck_reminders_custom_interval",
        ),
        CheckConstraint(
            "frequency != 'weekly' OR weekdays IS NULL OR cardinality(weekdays) > 0",
            name="ck_reminders_weekdays",
        ),
        Index("ix_reminders_due", "is_active", "remind_at"),
        Index("ix_reminders_user_active", "user_id", "is_active", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_recurring: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    frequency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_of_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weekdays: Mapped[list[str] | None] = mapped_column(ARRAY(String(3)), nullable=True)
    snooze_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh_key: Mapped[str] = mapped_column(Text, nullable=False)
    auth_key: Mapped[str] = mapped_column(Text, nullable=False)
    device_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationLog(Base):
    __tablename__ = "notification_log"
    __table_args__ = (
        CheckConstraint(
            "type IN ('push', 'in_app', 'budget_alert', 'cc_due')",
            name="ck_notification_log_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'read')",
            name="ck_notification_log_status",
        ),
        UniqueConstraint(
            "reminder_id",
            "occurrence_at",
            "type",
            name="uq_notification_log_reminder_occurrence_type",
        ),
        UniqueConstraint("event_key", name="uq_notification_log_event_key"),
        Index("ix_notification_log_user_status_sent", "user_id", "status", "sent_at"),
        Index("ix_notification_log_pending_push", "status", "type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reminder_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reminders.id", ondelete="SET NULL"), nullable=True
    )
    occurrence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    event_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
