from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
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


class MoodLog(Base):
    __tablename__ = "mood_logs"
    __table_args__ = (
        CheckConstraint("mood_score BETWEEN 1 AND 5", name="ck_mood_logs_score"),
        UniqueConstraint("user_id", "log_date", name="uq_mood_logs_user_date"),
        Index("ix_mood_logs_user_logged_at", "user_id", "logged_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mood_score: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(300), nullable=True)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SleepLog(Base):
    __tablename__ = "sleep_logs"
    __table_args__ = (
        CheckConstraint(
            "duration_hours > 0 AND duration_hours <= 24", name="ck_sleep_logs_duration"
        ),
        CheckConstraint("quality_rating BETWEEN 1 AND 5", name="ck_sleep_logs_quality"),
        Index("ix_sleep_logs_user_date", "user_id", "sleep_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    bedtime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    wake_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    quality_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sleep_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Habit(Base):
    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint(
            "frequency IN ('daily', 'specific_days', 'weekly_count')",
            name="ck_habits_frequency",
        ),
        CheckConstraint(
            "(frequency = 'daily' AND target_weekdays IS NULL AND weekly_target_count IS NULL) OR "
            "(frequency = 'specific_days' AND target_weekdays IS NOT NULL "
            "AND cardinality(target_weekdays) > 0 AND weekly_target_count IS NULL) OR "
            "(frequency = 'weekly_count' AND target_weekdays IS NULL "
            "AND weekly_target_count IS NOT NULL AND weekly_target_count BETWEEN 1 AND 7)",
            name="ck_habits_schedule",
        ),
        CheckConstraint(
            "current_streak >= 0 AND longest_streak >= current_streak",
            name="ck_habits_streaks",
        ),
        CheckConstraint(
            "colour_hex ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_habits_colour",
        ),
        Index("ix_habits_user_active", "user_id", "is_active", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    colour_hex: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#6366F1")
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    target_weekdays: Mapped[list[str] | None] = mapped_column(ARRAY(String(3)), nullable=True)
    weekly_target_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class HabitCompletion(Base):
    __tablename__ = "habit_completions"
    __table_args__ = (
        UniqueConstraint("habit_id", "completion_date", name="uq_habit_completions_habit_date"),
        Index("ix_habit_completions_user_date", "user_id", "completion_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    habit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    completion_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WaterLog(Base):
    __tablename__ = "water_logs"
    __table_args__ = (
        CheckConstraint("amount_ml > 0 AND amount_ml <= 5000", name="ck_water_logs_amount"),
        Index("ix_water_logs_user_date", "user_id", "log_date"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False, server_default="250")
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
