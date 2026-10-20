from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.note import Note


def list_notes(
    session: Session, user_id: UUID, query: str | None, limit: int, offset: int
) -> tuple[list[Note], int]:
    conditions = [Note.user_id == user_id, Note.deleted_at.is_(None)]
    if query:
        search_term = func.websearch_to_tsquery("simple", query)
        conditions.append(Note.search_vector.op("@@")(search_term))
        rank = func.ts_rank(Note.search_vector, search_term)
        statement = (
            select(Note)
            .where(*conditions)
            .order_by(rank.desc(), Note.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    else:
        statement = (
            select(Note)
            .where(*conditions)
            .order_by(Note.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
    items = list(session.scalars(statement))
    total = int(session.scalar(select(func.count()).select_from(Note).where(*conditions)) or 0)
    return items, total


def get_note(session: Session, user_id: UUID, note_id: UUID) -> Note | None:
    return session.scalar(
        select(Note).where(
            Note.id == note_id,
            Note.user_id == user_id,
            Note.deleted_at.is_(None),
        )
    )


def add_note(session: Session, note: Note) -> None:
    session.add(note)
