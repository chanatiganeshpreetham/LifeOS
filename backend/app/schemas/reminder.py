from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

ReminderFrequency = Literal["daily", "weekly", "monthly", "custom"]
ReminderTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]
ReminderNotes = Annotated[str, StringConstraints(max_length=10000)]
Weekday = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _validate_aware_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.utcoffset() is None:
        raise ValueError("Date and time must include a timezone.")
    return value


class ReminderCreate(BaseModel):
    title: ReminderTitle
    notes: ReminderNotes | None = None
    remind_at: datetime
    is_recurring: bool = False
    frequency: ReminderFrequency | None = None
    interval_days: int | None = Field(default=None, ge=1, le=365)
    weekdays: list[Weekday] | None = Field(default=None, max_length=7)

    _validate_remind_at = field_validator("remind_at")(_validate_aware_datetime)

    @model_validator(mode="after")
    def validate_schedule(self) -> "ReminderCreate":
        if self.is_recurring != (self.frequency is not None):
            raise ValueError("Choose a recurrence frequency for recurring reminders only.")
        if (self.frequency == "custom") != (self.interval_days is not None):
            raise ValueError("Custom recurrence requires an interval of 1 to 365 days.")
        if self.frequency != "weekly" and self.weekdays:
            raise ValueError("Weekdays can only be used for weekly reminders.")
        if self.frequency == "weekly" and self.weekdays is not None and not self.weekdays:
            raise ValueError("Choose at least one weekday.")
        if self.weekdays and len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError("Weekdays cannot contain duplicates.")
        return self


class ReminderUpdate(BaseModel):
    title: ReminderTitle | None = None
    notes: ReminderNotes | None = None
    remind_at: datetime | None = None
    is_recurring: bool | None = None
    frequency: ReminderFrequency | None = None
    interval_days: int | None = Field(default=None, ge=1, le=365)
    weekdays: list[Weekday] | None = Field(default=None, max_length=7)
    is_active: bool | None = None

    _validate_remind_at = field_validator("remind_at")(_validate_aware_datetime)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> "ReminderUpdate":
        for field in ("title", "remind_at", "is_recurring", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        if "title" in self.model_fields_set and not self.title:
            raise ValueError("title cannot be empty.")
        return self


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    notes: str | None
    remind_at: datetime
    is_recurring: bool
    frequency: ReminderFrequency | None
    interval_days: int | None
    weekdays: list[str] | None
    is_active: bool
    is_acknowledged: bool
    created_at: datetime
    updated_at: datetime


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    total: int


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reminder_id: UUID | None
    type: Literal["in_app", "budget_alert", "cc_due"]
    payload_summary: str | None
    sent_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int


class PushSubscriptionInput(BaseModel):
    endpoint: AnyHttpUrl
    p256dh_key: Annotated[str, StringConstraints(min_length=20, max_length=200)]
    auth_key: Annotated[str, StringConstraints(min_length=8, max_length=100)]
    device_label: Annotated[str | None, StringConstraints(max_length=100)] = None

    @field_validator("endpoint")
    @classmethod
    def require_secure_endpoint(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.scheme != "https":
            raise ValueError("Push subscription endpoint must use HTTPS.")
        if value.username or value.password:
            raise ValueError("Push subscription endpoint cannot include credentials.")
        host = value.host.lower().rstrip(".")
        try:
            ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("Push subscription endpoint must use a recognized push service.")
        if not (
            host == "fcm.googleapis.com"
            or host.endswith(".push.services.mozilla.com")
            or host.endswith(".push.apple.com")
        ):
            raise ValueError("Push subscription endpoint must use a recognized push service.")
        return value


class PushConfigResponse(BaseModel):
    enabled: bool
    public_key: str | None


class MessageResponse(BaseModel):
    message: str
