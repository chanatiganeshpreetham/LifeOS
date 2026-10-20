from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
HabitFrequency = Literal["daily", "specific_days", "weekly_count"]


class MoodInput(BaseModel):
    mood_score: int = Field(ge=1, le=5)


class MoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    mood_score: int
    logged_at: datetime
    log_date: date


class MoodHistoryResponse(BaseModel):
    items: list[MoodResponse]
    days: int


class SleepInput(BaseModel):
    bedtime: datetime
    wake_time: datetime
    quality_rating: int = Field(ge=1, le=5)

    @field_validator("bedtime", "wake_time")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("Sleep times must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_duration(self) -> "SleepInput":
        duration = (self.wake_time.astimezone(UTC) - self.bedtime.astimezone(UTC)).total_seconds()
        if duration <= 0 or duration > 24 * 60 * 60:
            raise ValueError("Sleep duration must be greater than zero and at most 24 hours.")
        return self


class SleepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bedtime: datetime
    wake_time: datetime
    duration_hours: float
    quality_rating: int
    sleep_date: date
    created_at: datetime


class SleepListResponse(BaseModel):
    items: list[SleepResponse]


class HabitInput(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
    colour_hex: Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")] = "#6366F1"
    frequency: HabitFrequency = "daily"
    target_weekdays: list[Weekday] | None = Field(default=None, max_length=7)
    weekly_target_count: int | None = Field(default=None, ge=1, le=7)

    @model_validator(mode="after")
    def validate_schedule(self) -> "HabitInput":
        if self.frequency == "daily" and (self.target_weekdays or self.weekly_target_count):
            raise ValueError("Daily habits do not use weekday or weekly targets.")
        if self.frequency == "specific_days":
            if not self.target_weekdays:
                raise ValueError("Choose at least one weekday for a specific-days habit.")
            if self.weekly_target_count is not None:
                raise ValueError("Specific-days habits do not use a weekly target count.")
        if self.frequency == "weekly_count":
            if self.weekly_target_count is None:
                raise ValueError("Choose a weekly completion target from 1 to 7.")
            if self.target_weekdays:
                raise ValueError("Weekly-count habits do not use specific weekdays.")
        if self.target_weekdays and len(set(self.target_weekdays)) != len(self.target_weekdays):
            raise ValueError("Weekdays cannot contain duplicates.")
        return self


class HabitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    colour_hex: str
    frequency: HabitFrequency
    target_weekdays: list[str] | None
    weekly_target_count: int | None
    current_streak: int
    longest_streak: int
    weekly_completed_count: int
    is_active: bool
    completed_today: bool


class HabitListResponse(BaseModel):
    items: list[HabitResponse]
    total: int


class WaterInput(BaseModel):
    amount_ml: int = Field(default=250, ge=1, le=5000)


class WaterLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    amount_ml: int
    logged_at: datetime


class WaterDayResponse(BaseModel):
    log_date: date
    total_ml: int
    goal_ml: int
    items: list[WaterLogResponse]
