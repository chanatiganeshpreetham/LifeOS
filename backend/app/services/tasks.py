from datetime import UTC, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.models.task import Task
from app.repositories import tasks as task_repository
from app.schemas.task import TaskCreate, TaskUpdate


def _now() -> datetime:
    return datetime.now(UTC)


def _day_bounds(user: User, now: datetime) -> tuple[datetime, datetime]:
    try:
        timezone = ZoneInfo(user.timezone)
    except ZoneInfoNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your profile timezone is invalid. Update it before filtering tasks by date.",
        ) from None

    local_today = now.astimezone(timezone).date()
    start = datetime.combine(local_today, time.min, tzinfo=timezone)
    end = datetime.combine(local_today + timedelta(days=1), time.min, tzinfo=timezone)
    return start.astimezone(UTC), end.astimezone(UTC)


def _get_owned_task(session: Session, user: User, task_id: UUID) -> Task:
    task = task_repository.get_task(session, user.id, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task


def list_tasks(
    session: Session,
    user: User,
    filter_name: str,
    search: str | None,
) -> list[Task]:
    now = _now()
    day_start, day_end = _day_bounds(user, now)
    return task_repository.list_tasks(
        session,
        user.id,
        filter_name,
        search.strip() if search and search.strip() else None,
        day_start,
        day_end,
        now,
    )


def dashboard_tasks(session: Session, user: User) -> dict[str, object]:
    now = _now()
    day_start, _ = _day_bounds(user, now)
    timezone = ZoneInfo(user.timezone)
    local_today = now.astimezone(timezone).date()
    day_end = datetime.combine(local_today + timedelta(days=8), time.min, tzinfo=timezone)
    open_conditions = (
        Task.user_id == user.id,
        Task.deleted_at.is_(None),
        Task.is_completed.is_(False),
    )
    open_count = int(
        session.scalar(select(func.count()).select_from(Task).where(*open_conditions)) or 0
    )
    overdue_count = int(
        session.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                *open_conditions,
                Task.due_at < now,
            )
        )
        or 0
    )
    upcoming = list(
        session.scalars(
            select(Task)
            .where(
                *open_conditions,
                Task.due_at.is_not(None),
                Task.due_at >= day_start,
                Task.due_at < day_end.astimezone(UTC),
            )
            .order_by(Task.due_at.asc())
            .limit(4)
        )
    )
    return {"open_count": open_count, "overdue_count": overdue_count, "upcoming": upcoming}


def get_task(session: Session, user: User, task_id: UUID) -> Task:
    return _get_owned_task(session, user, task_id)


def create_task(session: Session, user: User, payload: TaskCreate) -> Task:
    task = Task(
        user_id=user.id,
        title=payload.title,
        notes=payload.notes,
        priority=payload.priority,
        due_at=payload.due_at.astimezone(UTC) if payload.due_at else None,
    )
    task_repository.add_task(session, task)
    session.commit()
    session.refresh(task)
    return task


def update_task(
    session: Session,
    user: User,
    task_id: UUID,
    payload: TaskUpdate,
) -> Task:
    task = _get_owned_task(session, user, task_id)
    changes = payload.model_dump(exclude_unset=True)
    if "due_at" in changes and changes["due_at"] is not None:
        changes["due_at"] = changes["due_at"].astimezone(UTC)

    if "is_completed" in changes:
        is_completed = changes.pop("is_completed")
        if is_completed != task.is_completed:
            task.is_completed = is_completed
            task.completed_at = _now() if is_completed else None
    for field, value in changes.items():
        setattr(task, field, value)

    session.commit()
    session.refresh(task)
    return task


def delete_task(session: Session, user: User, task_id: UUID) -> None:
    task = _get_owned_task(session, user, task_id)
    task.deleted_at = _now()
    session.commit()
