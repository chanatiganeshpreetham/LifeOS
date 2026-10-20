from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.daybook import (
    DaybookActivityResponse,
    DaybookEntryCreate,
    DaybookEntryResponse,
    DaybookEntryUpdate,
    DaybookResponse,
)
from app.services import daybook as daybook_service

router = APIRouter(prefix="/daybook", tags=["daybook"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=DaybookResponse)
def get_daybook(
    session: SessionDependency,
    user: CurrentUser,
    start_date: Annotated[date, Query()],
    end_date: Annotated[date, Query()],
) -> DaybookResponse:
    entries, activities = daybook_service.get_daybook(session, user, start_date, end_date)
    return DaybookResponse(
        entries=[DaybookEntryResponse.model_validate(entry) for entry in entries],
        activities=[DaybookActivityResponse.model_validate(item) for item in activities],
    )


@router.post(
    "/entries",
    response_model=DaybookEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_entry(
    payload: DaybookEntryCreate, session: SessionDependency, user: CurrentUser
) -> DaybookEntryResponse:
    entry = daybook_service.create_entry(session, user, payload)
    return DaybookEntryResponse.model_validate(entry)


@router.patch("/entries/{entry_id}", response_model=DaybookEntryResponse)
def update_entry(
    entry_id: UUID,
    payload: DaybookEntryUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> DaybookEntryResponse:
    entry = daybook_service.update_entry(session, user, entry_id, payload)
    return DaybookEntryResponse.model_validate(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: UUID, session: SessionDependency, user: CurrentUser) -> Response:
    daybook_service.delete_entry(session, user, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
