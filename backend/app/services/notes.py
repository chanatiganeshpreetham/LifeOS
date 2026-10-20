from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.models.note import Note
from app.repositories import notes as note_repository
from app.schemas.note import NoteCreate, NoteUpdate


def _get_owned_note(session: Session, user: User, note_id: UUID) -> Note:
    note = note_repository.get_note(session, user.id, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return note


def list_notes(
    session: Session,
    user: User,
    query: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Note], int]:
    search_query = query.strip() if query and query.strip() else None
    return note_repository.list_notes(session, user.id, search_query, limit, offset)


def create_note(session: Session, user: User, payload: NoteCreate) -> Note:
    note = Note(user_id=user.id, **payload.model_dump())
    note_repository.add_note(session, note)
    session.commit()
    session.refresh(note)
    return note


def update_note(session: Session, user: User, note_id: UUID, payload: NoteUpdate) -> Note:
    note = _get_owned_note(session, user, note_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    session.commit()
    session.refresh(note)
    return note


def delete_note(session: Session, user: User, note_id: UUID) -> None:
    note = _get_owned_note(session, user, note_id)
    note.deleted_at = datetime.now(UTC)
    session.commit()
