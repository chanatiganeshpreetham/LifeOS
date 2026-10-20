from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.note import NoteCreate, NoteListResponse, NoteResponse, NoteUpdate
from app.services import notes as notes_service

router = APIRouter(prefix="/notes", tags=["notes"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=NoteListResponse)
def list_notes(
    session: SessionDependency,
    user: CurrentUser,
    query: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> NoteListResponse:
    notes, total = notes_service.list_notes(session, user, query, limit, offset)
    return NoteListResponse(items=notes, total=total)


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, session: SessionDependency, user: CurrentUser) -> NoteResponse:
    return NoteResponse.model_validate(notes_service.create_note(session, user, payload))


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: UUID,
    payload: NoteUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> NoteResponse:
    return NoteResponse.model_validate(notes_service.update_note(session, user, note_id, payload))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: UUID, session: SessionDependency, user: CurrentUser) -> Response:
    notes_service.delete_note(session, user, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
