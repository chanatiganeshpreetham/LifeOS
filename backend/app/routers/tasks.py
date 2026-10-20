from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.task import (
    TaskCreate,
    TaskDashboardResponse,
    TaskFilter,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
)
from app.services import tasks as task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/dashboard", response_model=TaskDashboardResponse)
def dashboard_tasks(session: SessionDependency, user: CurrentUser) -> TaskDashboardResponse:
    return TaskDashboardResponse(**task_service.dashboard_tasks(session, user))


@router.get("", response_model=TaskListResponse)
def list_tasks(
    session: SessionDependency,
    user: CurrentUser,
    filter_name: Annotated[str, Query(alias="filter")] = TaskFilter.ALL,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> TaskListResponse:
    if filter_name not in TaskFilter.values():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filter must be all, today, overdue, or completed.",
        )
    tasks = task_service.list_tasks(session, user, filter_name, search)
    return TaskListResponse(items=tasks, total=len(tasks))


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    session: SessionDependency,
    user: CurrentUser,
) -> TaskResponse:
    return TaskResponse.model_validate(task_service.create_task(session, user, payload))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    session: SessionDependency,
    user: CurrentUser,
) -> TaskResponse:
    return TaskResponse.model_validate(task_service.get_task(session, user, task_id))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> TaskResponse:
    return TaskResponse.model_validate(task_service.update_task(session, user, task_id, payload))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    session: SessionDependency,
    user: CurrentUser,
) -> Response:
    task_service.delete_task(session, user, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
