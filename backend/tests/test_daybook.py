from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.models.reminder import Reminder
from app.services.reminders import occurrences_between


def _reminder(
    remind_at: datetime,
    frequency: str,
    weekdays: list[str] | None = None,
    interval_days: int | None = None,
    day_of_month: int | None = None,
) -> Reminder:
    return Reminder(
        title="Test reminder",
        remind_at=remind_at,
        is_recurring=True,
        frequency=frequency,
        weekdays=weekdays,
        interval_days=interval_days,
        day_of_month=day_of_month,
    )


def test_daily_reminder_occurrences_skip_past_dates() -> None:
    reminder = _reminder(datetime(2020, 1, 1, 9, tzinfo=UTC), "daily")
    occurrences = occurrences_between(
        reminder,
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 4, tzinfo=UTC),
        ZoneInfo("UTC"),
    )

    assert [item.date() for item in occurrences] == [
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
    ]


def test_weekly_reminder_occurrences_respect_selected_weekdays() -> None:
    reminder = _reminder(
        datetime(2026, 9, 28, 9, tzinfo=UTC),
        "weekly",
        weekdays=["tue", "thu"],
    )
    occurrences = occurrences_between(
        reminder,
        datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 8, tzinfo=UTC),
        ZoneInfo("UTC"),
    )

    assert [item.date() for item in occurrences] == [
        date(2026, 10, 1),
        date(2026, 10, 6),
    ]


def test_monthly_reminder_clamps_day_to_month_length() -> None:
    timezone = ZoneInfo("Asia/Kolkata")
    reminder = _reminder(
        datetime(2026, 1, 31, 9, tzinfo=timezone),
        "monthly",
        day_of_month=31,
    )
    occurrences = occurrences_between(
        reminder,
        datetime(2026, 2, 1, tzinfo=timezone).astimezone(UTC),
        datetime(2026, 3, 1, tzinfo=timezone).astimezone(UTC),
        timezone,
    )

    assert [item.astimezone(timezone).date() for item in occurrences] == [date(2026, 2, 28)]
