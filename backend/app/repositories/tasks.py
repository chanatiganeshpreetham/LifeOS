from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.task import Task


def list_tasks(
    session: Session,
    user_id: UUID,
    filter_name: str,
    search: str | None,
    day_start: datetime,
    day_end: datetime,
    now: datetime,
) -> list[Task]:
    statement = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))

    if filter_name == "today":
        statement = statement.where(Task.due_at >= day_start, Task.due_at < day_end)
    elif filter_name == "overdue":
        statement = statement.where(Task.is_completed.is_(False), Task.due_at < now)
    elif filter_name == "completed":
        statement = statement.where(Task.is_completed.is_(True))

    if search:
        statement = statement.where(
            Task.search_vector.op("@@")(func.plainto_tsquery("simple", search))
        )

    statement = statement.order_by(
        case((Task.is_completed.is_(True), 1), else_=0),
        Task.due_at.asc().nulls_last(),
        Task.created_at.desc(),
    )
    return list(session.scalars(statement))


def get_task(session: Session, user_id: UUID, task_id: UUID) -> Task | None:
    return session.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == user_id,
            Task.deleted_at.is_(None),
        )
    )


def add_task(session: Session, task: Task) -> None:
    session.add(task)
