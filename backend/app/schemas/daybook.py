from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

EntryTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
EntryContent = Annotated[str, StringConstraints(max_length=100000)]
ActivitySource = Literal["tasks", "reminders", "finance", "health", "notes"]


class DaybookEntryCreate(BaseModel):
    entry_date: date
    title: EntryTitle = "Untitled entry"
    content: EntryContent = ""


class DaybookEntryUpdate(BaseModel):
    entry_date: date | None = None
    title: EntryTitle | None = None
    content: EntryContent | None = None

    @model_validator(mode="after")
    def validate_changes(self) -> "DaybookEntryUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide a date, title, or content to update.")
        for field in ("entry_date", "title", "content"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class DaybookEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entry_date: date
    title: str
    content: str
    created_at: datetime
    updated_at: datetime


class DaybookActivityResponse(BaseModel):
    id: str
    activity_date: date
    title: str
    description: str | None
    source: ActivitySource
    status: str | None
    url: str
    occurred_at: datetime | None = None


class DaybookResponse(BaseModel):
    entries: list[DaybookEntryResponse]
    activities: list[DaybookActivityResponse]
