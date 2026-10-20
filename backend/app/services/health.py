from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.models.health import Habit, HabitCompletion, MoodLog, SleepLog, WaterLog
from app.repositories import health as health_repository
from app.schemas.health import HabitInput, MoodInput, SleepInput, WaterInput

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your profile timezone is invalid. Update it before logging health data.",
        ) from None


def local_today(user: User, now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(_timezone(user)).date()


def get_mood_today(session: Session, user: User) -> MoodLog | None:
    return health_repository.get_mood_log(session, user.id, local_today(user))


def save_mood(session: Session, user: User, payload: MoodInput) -> MoodLog:
    today = local_today(user)
    health_repository.user_row_lock(session, user.id)
    mood = health_repository.get_mood_log(session, user.id, today)
    if mood is None:
        mood = MoodLog(
            user_id=user.id,
            mood_score=payload.mood_score,
            notes=None,
            logged_at=datetime.now(UTC),
            log_date=today,
        )
        session.add(mood)
    else:
        mood.mood_score = payload.mood_score
        mood.logged_at = datetime.now(UTC)
    session.commit()
    session.refresh(mood)
    return mood


def list_moods(session: Session, user: User, days: int) -> list[MoodLog]:
    today = local_today(user)
    return health_repository.list_mood_logs(
        session,
        user.id,
        today - timedelta(days=days - 1),
        today,
    )


def log_sleep(session: Session, user: User, payload: SleepInput) -> SleepLog:
    wake_time = payload.wake_time.astimezone(UTC)
    bedtime = payload.bedtime.astimezone(UTC)
    duration_hours = (wake_time - bedtime).total_seconds() / 3600
    sleep_log = SleepLog(
        user_id=user.id,
        bedtime=bedtime,
        wake_time=wake_time,
        duration_hours=round(duration_hours, 2),
        quality_rating=payload.quality_rating,
        notes=None,
        sleep_date=wake_time.astimezone(_timezone(user)).date(),
    )
    session.add(sleep_log)
    session.commit()
    session.refresh(sleep_log)
    return sleep_log


def list_sleep_logs(session: Session, user: User, days: int) -> list[SleepLog]:
    today = local_today(user)
    return health_repository.list_sleep_logs(
        session,
        user.id,
        today - timedelta(days=days - 1),
        today,
    )


def _habit_get(session: Session, user: User, habit_id: UUID, lock: bool = False) -> Habit:
    habit = health_repository.get_habit(session, user.id, habit_id, lock)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found.")
    return habit


def _habit_start_date(habit: Habit, timezone: ZoneInfo) -> date:
    return habit.created_at.astimezone(timezone).date()


def _streaks(
    habit: Habit, completed: list[date], today: date, timezone: ZoneInfo
) -> tuple[int, int]:
    dates = set(completed)
    start_date = _habit_start_date(habit, timezone)
    if habit.frequency == "weekly_count":
        first_week = start_date - timedelta(days=start_date.weekday())
        current_week = today - timedelta(days=today.weekday())
        week_counts: dict[date, int] = {}
        for completion in dates:
            week = completion - timedelta(days=completion.weekday())
            week_counts[week] = week_counts.get(week, 0) + 1
        target = habit.weekly_target_count or 1
        week_starts = []
        week = first_week
        while week <= current_week:
            week_starts.append(week)
            week += timedelta(days=7)
        run = longest = 0
        for week in week_starts:
            if week_counts.get(week, 0) >= target:
                run += 1
                longest = max(longest, run)
            else:
                run = 0
        if week_counts.get(current_week, 0) >= target:
            anchor = current_week
        elif today.weekday() < 6:
            anchor = current_week - timedelta(days=7)
        else:
            anchor = None
        current = 0
        while anchor is not None and anchor >= first_week and week_counts.get(anchor, 0) >= target:
            current += 1
            anchor -= timedelta(days=7)
        return current, longest

    scheduled = []
    day = start_date
    weekdays = set(habit.target_weekdays or [])
    while day <= today:
        if habit.frequency == "daily" or _WEEKDAYS[day.weekday()] in weekdays:
            scheduled.append(day)
        day += timedelta(days=1)

    run = longest = 0
    for scheduled_day in scheduled:
        if scheduled_day in dates:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    anchor_index = len(scheduled) - 1
    if anchor_index >= 0 and scheduled[anchor_index] == today and today not in dates:
        anchor_index -= 1
    current = 0
    for scheduled_day in reversed(scheduled[: anchor_index + 1]):
        if scheduled_day not in dates:
            break
        current += 1
    return current, longest


def _refresh_streaks(session: Session, user: User, habit: Habit) -> None:
    timezone = _timezone(user)
    completions = health_repository.list_completion_dates(session, habit.id)
    current, longest = _streaks(habit, completions, local_today(user), timezone)
    habit.current_streak = current
    habit.longest_streak = max(habit.longest_streak, longest)


def list_habits(
    session: Session, user: User
) -> tuple[list[Habit], set[UUID], dict[UUID, int], dict[UUID, tuple[int, int]]]:
    habits = health_repository.list_habits(session, user.id)
    today = local_today(user)
    timezone = _timezone(user)
    week_start = today - timedelta(days=today.weekday())
    completed = {
        habit.id for habit in habits if health_repository.has_completion(session, habit.id, today)
    }
    weekly_counts = {}
    streaks = {}
    for habit in habits:
        dates = health_repository.list_completion_dates(session, habit.id)
        weekly_counts[habit.id] = sum(week_start <= item <= today for item in dates)
        current, longest = _streaks(habit, dates, today, timezone)
        streaks[habit.id] = (current, max(habit.longest_streak, longest))
    return habits, completed, weekly_counts, streaks


def habit_weekly_count(session: Session, user: User, habit: Habit) -> int:
    today = local_today(user)
    week_start = today - timedelta(days=today.weekday())
    return sum(
        week_start <= item <= today
        for item in health_repository.list_completion_dates(session, habit.id)
    )


def create_habit(session: Session, user: User, payload: HabitInput) -> Habit:
    _timezone(user)
    habit = Habit(
        user_id=user.id,
        name=payload.name,
        colour_hex=payload.colour_hex,
        frequency=payload.frequency,
        target_weekdays=list(payload.target_weekdays) if payload.target_weekdays else None,
        weekly_target_count=payload.weekly_target_count,
    )
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit


def update_habit(session: Session, user: User, habit_id: UUID, payload: HabitInput) -> Habit:
    habit = _habit_get(session, user, habit_id, lock=True)
    habit.name = payload.name
    habit.colour_hex = payload.colour_hex
    habit.frequency = payload.frequency
    habit.target_weekdays = list(payload.target_weekdays) if payload.target_weekdays else None
    habit.weekly_target_count = payload.weekly_target_count
    _refresh_streaks(session, user, habit)
    session.commit()
    session.refresh(habit)
    return habit


def complete_habit(session: Session, user: User, habit_id: UUID) -> Habit:
    habit = _habit_get(session, user, habit_id, lock=True)
    today = local_today(user)
    if habit.frequency == "specific_days" and _WEEKDAYS[today.weekday()] not in (
        habit.target_weekdays or []
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This habit is not scheduled for today.",
        )
    if not health_repository.has_completion(session, habit.id, today):
        health_repository.add_completion(
            session,
            HabitCompletion(habit_id=habit.id, user_id=user.id, completion_date=today),
        )
        session.flush()
        _refresh_streaks(session, user, habit)
        session.commit()
        session.refresh(habit)
    return habit


def get_water_today(session: Session, user: User) -> tuple[date, int, int, list[WaterLog]]:
    today = local_today(user)
    logs = health_repository.list_water_logs(session, user.id, today)
    total = health_repository.water_total(session, user.id, today)
    goal = round(user.water_goal_litres * 1000)
    return today, total, goal, logs


def add_water(session: Session, user: User, payload: WaterInput) -> WaterLog:
    now = datetime.now(UTC)
    water_log = WaterLog(
        user_id=user.id,
        amount_ml=payload.amount_ml,
        logged_at=now,
        log_date=now.astimezone(_timezone(user)).date(),
    )
    health_repository.add_water_log(session, water_log)
    session.commit()
    session.refresh(water_log)
    return water_log
