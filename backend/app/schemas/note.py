from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

NoteTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
NoteBody = Annotated[str, StringConstraints(max_length=100000)]


class NoteCreate(BaseModel):
    title: NoteTitle = "Untitled note"
    body: NoteBody | None = None


class NoteUpdate(BaseModel):
    title: NoteTitle | None = None
    body: NoteBody | None = None

    @model_validator(mode="after")
    def reject_null_title(self) -> "NoteUpdate":
        if "title" in self.model_fields_set and self.title is None:
            raise ValueError("title cannot be null.")
        if not self.model_fields_set:
            raise ValueError("Provide a title or body to update.")
        return self


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str | None
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    items: list[NoteResponse]
    total: int
