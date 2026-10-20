"""Add health tracking and full-text notes.

Revision ID: 0006_health_notes
Revises: 0005_finance
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_health_notes"
down_revision: str | None = "0005_finance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mood_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.String(length=300), nullable=True),
        sa.Column(
            "logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("mood_score BETWEEN 1 AND 5", name="ck_mood_logs_score"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "log_date", name="uq_mood_logs_user_date"),
    )
    op.create_index("ix_mood_logs_user_logged_at", "mood_logs", ["user_id", "logged_at"])

    op.create_table(
        "sleep_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("bedtime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("wake_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_hours", sa.Float(), nullable=False),
        sa.Column("quality_rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sleep_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_hours > 0 AND duration_hours <= 24",
            name="ck_sleep_logs_duration",
        ),
        sa.CheckConstraint("quality_rating BETWEEN 1 AND 5", name="ck_sleep_logs_quality"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sleep_logs_user_date", "sleep_logs", ["user_id", "sleep_date"])

    op.create_table(
        "habits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("colour_hex", sa.String(length=7), server_default="#6366F1", nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("target_weekdays", postgresql.ARRAY(sa.String(length=3)), nullable=True),
        sa.Column("weekly_target_count", sa.Integer(), nullable=True),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "frequency IN ('daily', 'specific_days', 'weekly_count')",
            name="ck_habits_frequency",
        ),
        sa.CheckConstraint(
            "(frequency = 'daily' AND target_weekdays IS NULL AND weekly_target_count IS NULL) OR "
            "(frequency = 'specific_days' AND target_weekdays IS NOT NULL "
            "AND cardinality(target_weekdays) > 0 AND weekly_target_count IS NULL) OR "
            "(frequency = 'weekly_count' AND target_weekdays IS NULL "
            "AND weekly_target_count IS NOT NULL AND weekly_target_count BETWEEN 1 AND 7)",
            name="ck_habits_schedule",
        ),
        sa.CheckConstraint(
            "current_streak >= 0 AND longest_streak >= current_streak",
            name="ck_habits_streaks",
        ),
        sa.CheckConstraint("colour_hex ~ '^#[0-9A-Fa-f]{6}$'", name="ck_habits_colour"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_habits_user_active", "habits", ["user_id", "is_active", "deleted_at"])

    op.create_table(
        "habit_completions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("habit_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("completion_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["habit_id"], ["habits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "habit_id",
            "completion_date",
            name="uq_habit_completions_habit_date",
        ),
    )
    op.create_index(
        "ix_habit_completions_user_date",
        "habit_completions",
        ["user_id", "completion_date"],
    )

    op.create_table(
        "water_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount_ml", sa.Integer(), server_default="250", nullable=False),
        sa.Column(
            "logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount_ml > 0 AND amount_ml <= 5000", name="ck_water_logs_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_water_logs_user_date", "water_logs", ["user_id", "log_date"])

    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_user_updated", "notes", ["user_id", "updated_at"])
    op.create_index(
        "ix_notes_search_vector",
        "notes",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.execute(
        """
        CREATE FUNCTION update_note_search_vector() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.body, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER notes_search_vector_update
        BEFORE INSERT OR UPDATE OF title, body ON notes
        FOR EACH ROW EXECUTE FUNCTION update_note_search_vector()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER notes_search_vector_update ON notes")
    op.execute("DROP FUNCTION update_note_search_vector()")
    op.drop_index("ix_notes_search_vector", table_name="notes")
    op.drop_index("ix_notes_user_updated", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_water_logs_user_date", table_name="water_logs")
    op.drop_table("water_logs")
    op.drop_index("ix_habit_completions_user_date", table_name="habit_completions")
    op.drop_table("habit_completions")
    op.drop_index("ix_habits_user_active", table_name="habits")
    op.drop_table("habits")
    op.drop_index("ix_sleep_logs_user_date", table_name="sleep_logs")
    op.drop_table("sleep_logs")
    op.drop_index("ix_mood_logs_user_logged_at", table_name="mood_logs")
    op.drop_table("mood_logs")
