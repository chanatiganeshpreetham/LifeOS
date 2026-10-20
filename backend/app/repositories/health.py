from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.health import Habit, HabitCompletion, MoodLog, SleepLog, WaterLog


def get_mood_log(session: Session, user_id: UUID, log_date: date) -> MoodLog | None:
    return session.scalar(
        select(MoodLog).where(MoodLog.user_id == user_id, MoodLog.log_date == log_date)
    )


def list_mood_logs(
    session: Session, user_id: UUID, start_date: date, end_date: date
) -> list[MoodLog]:
    return list(
        session.scalars(
            select(MoodLog)
            .where(
                MoodLog.user_id == user_id,
                MoodLog.log_date >= start_date,
                MoodLog.log_date <= end_date,
            )
            .order_by(MoodLog.log_date.asc())
        )
    )


def list_sleep_logs(
    session: Session, user_id: UUID, start_date: date, end_date: date
) -> list[SleepLog]:
    return list(
        session.scalars(
            select(SleepLog)
            .where(
                SleepLog.user_id == user_id,
                SleepLog.sleep_date >= start_date,
                SleepLog.sleep_date <= end_date,
            )
            .order_by(SleepLog.wake_time.desc())
        )
    )


def list_habits(session: Session, user_id: UUID) -> list[Habit]:
    return list(
        session.scalars(
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
                Habit.deleted_at.is_(None),
            )
            .order_by(Habit.created_at.asc())
        )
    )


def get_habit(session: Session, user_id: UUID, habit_id: UUID, lock: bool = False) -> Habit | None:
    query = select(Habit).where(
        Habit.id == habit_id,
        Habit.user_id == user_id,
        Habit.deleted_at.is_(None),
    )
    if lock:
        query = query.with_for_update()
    return session.scalar(query)


def list_completion_dates(session: Session, habit_id: UUID) -> list[date]:
    return list(
        session.scalars(
            select(HabitCompletion.completion_date)
            .where(HabitCompletion.habit_id == habit_id)
            .order_by(HabitCompletion.completion_date.asc())
        )
    )


def has_completion(session: Session, habit_id: UUID, completion_date: date) -> bool:
    return (
        session.scalar(
            select(HabitCompletion.id).where(
                HabitCompletion.habit_id == habit_id,
                HabitCompletion.completion_date == completion_date,
            )
        )
        is not None
    )


def add_completion(session: Session, completion: HabitCompletion) -> None:
    session.add(completion)


def list_water_logs(session: Session, user_id: UUID, log_date: date) -> list[WaterLog]:
    return list(
        session.scalars(
            select(WaterLog)
            .where(WaterLog.user_id == user_id, WaterLog.log_date == log_date)
            .order_by(WaterLog.logged_at.desc())
        )
    )


def water_total(session: Session, user_id: UUID, log_date: date) -> int:
    return int(
        session.scalar(
            select(func.coalesce(func.sum(WaterLog.amount_ml), 0)).where(
                WaterLog.user_id == user_id,
                WaterLog.log_date == log_date,
            )
        )
        or 0
    )


def add_water_log(session: Session, log: WaterLog) -> None:
    session.add(log)


def user_row_lock(session: Session, user_id: UUID) -> None:
    session.execute(select(User.id).where(User.id == user_id).with_for_update())
