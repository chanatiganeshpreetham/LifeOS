"""Add reminders, push subscriptions, and in-app notifications.

Revision ID: 0004_reminders_push
Revises: 0003_tasks
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_reminders_push"
down_revision: str | None = "0003_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("day_of_month", sa.Integer(), nullable=True),
        sa.Column("weekdays", postgresql.ARRAY(sa.String(length=3)), nullable=True),
        sa.Column("snooze_minutes", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "frequency IS NULL OR frequency IN ('daily', 'weekly', 'monthly', 'custom')",
            name="ck_reminders_frequency",
        ),
        sa.CheckConstraint(
            "(is_recurring AND frequency IS NOT NULL) OR (NOT is_recurring AND frequency IS NULL)",
            name="ck_reminders_recurring_frequency",
        ),
        sa.CheckConstraint(
            "frequency != 'custom' OR "
            "(interval_days IS NOT NULL AND interval_days BETWEEN 1 AND 365)",
            name="ck_reminders_custom_interval",
        ),
        sa.CheckConstraint(
            "frequency != 'weekly' OR weekdays IS NULL OR cardinality(weekdays) > 0",
            name="ck_reminders_weekdays",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_due", "reminders", ["is_active", "remind_at"])
    op.create_index(
        "ix_reminders_user_active",
        "reminders",
        ["user_id", "is_active", "deleted_at"],
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh_key", sa.Text(), nullable=False),
        sa.Column("auth_key", sa.Text(), nullable=False),
        sa.Column("device_label", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])

    op.create_table(
        "notification_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reminder_id", sa.Uuid(), nullable=True),
        sa.Column("occurrence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("payload_summary", sa.Text(), nullable=True),
        sa.Column(
            "sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("type IN ('push', 'in_app')", name="ck_notification_log_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'read')",
            name="ck_notification_log_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reminder_id"], ["reminders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reminder_id",
            "occurrence_at",
            "type",
            name="uq_notification_log_reminder_occurrence_type",
        ),
    )
    op.create_index(
        "ix_notification_log_user_status_sent",
        "notification_log",
        ["user_id", "status", "sent_at"],
    )
    op.create_index(
        "ix_notification_log_pending_push",
        "notification_log",
        ["status", "type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_log_pending_push", table_name="notification_log")
    op.drop_index("ix_notification_log_user_status_sent", table_name="notification_log")
    op.drop_table("notification_log")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_index("ix_reminders_user_active", table_name="reminders")
    op.drop_index("ix_reminders_due", table_name="reminders")
    op.drop_table("reminders")
