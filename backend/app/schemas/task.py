from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

TaskPriority = Literal["high", "medium", "low"]
TaskTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
TaskNotes = Annotated[str, StringConstraints(max_length=10000)]


def _validate_due_at(value: datetime | None) -> datetime | None:
    if value is not None and value.utcoffset() is None:
        raise ValueError("Due date and time must include a timezone.")
    return value


class TaskCreate(BaseModel):
    title: TaskTitle
    notes: TaskNotes | None = None
    priority: TaskPriority = "medium"
    due_at: datetime | None = None

    _validate_due_at = field_validator("due_at")(_validate_due_at)


class TaskUpdate(BaseModel):
    title: TaskTitle | None = None
    notes: TaskNotes | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    is_completed: bool | None = None

    _validate_due_at = field_validator("due_at")(_validate_due_at)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "TaskUpdate":
        for field in ("title", "priority", "is_completed"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if "title" in self.model_fields_set and not self.title:
            raise ValueError("title cannot be empty.")
        return self


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    notes: str | None
    priority: TaskPriority
    due_at: datetime | None
    is_completed: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int


class TaskDashboardResponse(BaseModel):
    open_count: int
    overdue_count: int
    upcoming: list[TaskResponse]


class TaskFilter:
    ALL = "all"
    TODAY = "today"
    OVERDUE = "overdue"
    COMPLETED = "completed"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return cls.ALL, cls.TODAY, cls.OVERDUE, cls.COMPLETED
