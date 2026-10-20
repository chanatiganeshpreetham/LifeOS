from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    DaybookEntry,
    Expense,
    ExpenseCategory,
    FinanceEntry,
    Habit,
    HabitCompletion,
    MoodLog,
    Note,
    Reminder,
    SleepLog,
    Task,
    User,
    WaterLog,
)
from app.schemas.daybook import DaybookEntryCreate, DaybookEntryUpdate
from app.services.reminders import occurrences_between


def _timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your profile timezone is invalid. Update it before using Daybook.",
        ) from None


def _bounds(start_date: date, end_date: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    if end_date <= start_date or (end_date - start_date).days > 62:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose a date range of 1 to 62 days.",
        )
    start = datetime.combine(start_date, time.min, tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(end_date, time.min, tzinfo=timezone).astimezone(UTC)
    return start, end


def _entry(session: Session, user: User, entry_id: UUID) -> DaybookEntry:
    entry = session.scalar(
        select(DaybookEntry).where(
            DaybookEntry.id == entry_id,
            DaybookEntry.user_id == user.id,
        )
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Daybook entry not found.",
        )
    return entry


def create_entry(session: Session, user: User, payload: DaybookEntryCreate) -> DaybookEntry:
    entry = DaybookEntry(user_id=user.id, **payload.model_dump())
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def update_entry(
    session: Session, user: User, entry_id: UUID, payload: DaybookEntryUpdate
) -> DaybookEntry:
    entry = _entry(session, user, entry_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry(session: Session, user: User, entry_id: UUID) -> None:
    entry = _entry(session, user, entry_id)
    session.delete(entry)
    session.commit()


def get_daybook(
    session: Session, user: User, start_date: date, end_date: date
) -> tuple[list[DaybookEntry], list[dict[str, object]]]:
    timezone = _timezone(user)
    start_at, end_at = _bounds(start_date, end_date, timezone)
    entries = list(
        session.scalars(
            select(DaybookEntry)
            .where(
                DaybookEntry.user_id == user.id,
                DaybookEntry.entry_date >= start_date,
                DaybookEntry.entry_date < end_date,
            )
            .order_by(DaybookEntry.entry_date, DaybookEntry.created_at)
        )
    )
    activities: list[dict[str, object]] = []

    tasks = session.scalars(
        select(Task).where(
            Task.user_id == user.id,
            Task.deleted_at.is_(None),
            or_(
                (Task.due_at >= start_at) & (Task.due_at < end_at),
                (Task.completed_at >= start_at) & (Task.completed_at < end_at),
                (Task.updated_at >= start_at) & (Task.updated_at < end_at),
            ),
        )
    )
    for task in tasks:
        completed_in_range = (
            task.completed_at is not None and start_at <= task.completed_at < end_at
        )
        due_in_range = task.due_at is not None and start_at <= task.due_at < end_at
        if task.is_completed and completed_in_range:
            event_at = task.completed_at
        elif due_in_range:
            event_at = task.due_at
        else:
            event_at = task.updated_at
        activities.append(
            _activity(
                "task",
                task.id,
                event_at.astimezone(timezone).date(),
                task.title,
                task.notes,
                "tasks",
                "Completed" if task.is_completed else "Open",
                "/tasks",
                event_at,
            )
        )

    notes = session.scalars(
        select(Note).where(
            Note.user_id == user.id,
            Note.deleted_at.is_(None),
            Note.updated_at >= start_at,
            Note.updated_at < end_at,
        )
    )
    for note in notes:
        activities.append(
            _activity(
                "note",
                note.id,
                note.updated_at.astimezone(timezone).date(),
                f"Note updated · {note.title}",
                (note.body or "").strip()[:300] or None,
                "notes",
                "Updated",
                "/notes",
                note.updated_at,
            )
        )

    reminders = session.scalars(
        select(Reminder).where(
            Reminder.user_id == user.id,
            Reminder.is_active.is_(True),
            Reminder.deleted_at.is_(None),
            Reminder.remind_at < end_at,
        )
    )
    for reminder in reminders:
        for occurrence in occurrences_between(reminder, start_at, end_at, timezone):
            _append_reminder(activities, reminder, occurrence, timezone)

    expenses = session.execute(
        select(Expense, ExpenseCategory.name)
        .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
        .where(
            Expense.user_id == user.id,
            Expense.deleted_at.is_(None),
            Expense.expense_date >= start_date,
            Expense.expense_date < end_date,
        )
    )
    for expense, category_name in expenses:
        activities.append(
            _activity(
                "expense",
                expense.id,
                expense.expense_date,
                expense.merchant or category_name,
                f"{expense.currency} {expense.amount:.2f}"
                + (f" · {expense.notes}" if expense.notes else ""),
                "finance",
                "Expense",
                "/finance",
                expense.created_at,
            )
        )

    finance_entries = session.scalars(
        select(FinanceEntry).where(
            FinanceEntry.user_id == user.id,
            FinanceEntry.deleted_at.is_(None),
            FinanceEntry.entry_date >= start_date,
            FinanceEntry.entry_date < end_date,
        )
    )
    for entry in finance_entries:
        activities.append(
            _activity(
                "finance",
                entry.id,
                entry.entry_date,
                f"{entry.entry_type.replace('_', ' ').title()} · {entry.source}",
                f"Amount {entry.amount:.2f}" + (f" · {entry.notes}" if entry.notes else ""),
                "finance",
                entry.entry_type.replace("_", " ").title(),
                "/finance",
                entry.created_at,
            )
        )

    for mood in session.scalars(
        select(MoodLog).where(
            MoodLog.user_id == user.id,
            MoodLog.log_date >= start_date,
            MoodLog.log_date < end_date,
        )
    ):
        activities.append(
            _activity(
                "mood",
                mood.id,
                mood.log_date,
                f"Mood check-in · {mood.mood_score}/5",
                mood.notes,
                "health",
                "Logged",
                "/health",
                mood.logged_at,
            )
        )

    for sleep in session.scalars(
        select(SleepLog).where(
            SleepLog.user_id == user.id,
            SleepLog.sleep_date >= start_date,
            SleepLog.sleep_date < end_date,
        )
    ):
        activities.append(
            _activity(
                "sleep",
                sleep.id,
                sleep.sleep_date,
                f"Sleep · {sleep.duration_hours:g} hours",
                f"Quality {sleep.quality_rating}/5" + (f" · {sleep.notes}" if sleep.notes else ""),
                "health",
                "Logged",
                "/health",
                sleep.wake_time,
            )
        )

    habits = session.execute(
        select(HabitCompletion, Habit.name)
        .join(Habit, Habit.id == HabitCompletion.habit_id)
        .where(
            HabitCompletion.user_id == user.id,
            HabitCompletion.completion_date >= start_date,
            HabitCompletion.completion_date < end_date,
            Habit.deleted_at.is_(None),
        )
    )
    for completion, habit_name in habits:
        activities.append(
            _activity(
                "habit",
                completion.id,
                completion.completion_date,
                f"Habit completed · {habit_name}",
                None,
                "health",
                "Completed",
                "/health",
                completion.created_at,
            )
        )

    water = session.execute(
        select(
            WaterLog.log_date,
            func.sum(WaterLog.amount_ml),
            func.min(WaterLog.logged_at),
        )
        .where(
            WaterLog.user_id == user.id,
            WaterLog.log_date >= start_date,
            WaterLog.log_date < end_date,
        )
        .group_by(WaterLog.log_date)
    )
    for log_date, amount_ml, logged_at in water:
        activities.append(
            _activity(
                "water",
                f"{user.id}:{log_date.isoformat()}",
                log_date,
                "Water logged",
                f"{int(amount_ml)} ml total",
                "health",
                "Logged",
                "/health",
                logged_at,
            )
        )

    activities.sort(
        key=lambda activity: (
            activity["activity_date"],
            activity["occurred_at"] or datetime.min.replace(tzinfo=UTC),
        )
    )
    return entries, activities


def _activity(
    kind: str,
    record_id: UUID | str,
    activity_date: date,
    title: str,
    description: str | None,
    source: str,
    status_text: str | None,
    url: str,
    occurred_at: datetime | None,
) -> dict[str, object]:
    return {
        "id": f"{kind}:{record_id}",
        "activity_date": activity_date,
        "title": title,
        "description": description,
        "source": source,
        "status": status_text,
        "url": url,
        "occurred_at": occurred_at,
    }


def _append_reminder(
    activities: list[dict[str, object]],
    reminder: Reminder,
    occurrence: datetime,
    timezone: ZoneInfo,
) -> None:
    activities.append(
        _activity(
            "reminder",
            f"{reminder.id}:{occurrence.isoformat()}",
            occurrence.astimezone(timezone).date(),
            reminder.title,
            reminder.notes,
            "reminders",
            "Acknowledged" if reminder.is_acknowledged else "Scheduled",
            "/reminders",
            occurrence,
        )
    )
