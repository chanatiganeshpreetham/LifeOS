from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.models.health import Habit
from app.schemas.health import (
    HabitInput,
    HabitListResponse,
    HabitResponse,
    MoodHistoryResponse,
    MoodInput,
    MoodResponse,
    SleepInput,
    SleepListResponse,
    SleepResponse,
    WaterDayResponse,
    WaterInput,
    WaterLogResponse,
)
from app.services import health as health_service

router = APIRouter(prefix="/health", tags=["health"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _habit_response(
    habit: Habit,
    completed_today: bool = False,
    weekly_completed_count: int = 0,
    current_streak: int | None = None,
    longest_streak: int | None = None,
) -> HabitResponse:
    return HabitResponse(
        id=habit.id,
        name=habit.name,
        colour_hex=habit.colour_hex,
        frequency=habit.frequency,
        target_weekdays=habit.target_weekdays,
        weekly_target_count=habit.weekly_target_count,
        current_streak=habit.current_streak if current_streak is None else current_streak,
        longest_streak=habit.longest_streak if longest_streak is None else longest_streak,
        weekly_completed_count=weekly_completed_count,
        is_active=habit.is_active,
        completed_today=completed_today,
    )


@router.get("/mood", response_model=MoodResponse | None)
def get_mood_today(session: SessionDependency, user: CurrentUser) -> MoodResponse | None:
    mood = health_service.get_mood_today(session, user)
    return MoodResponse.model_validate(mood) if mood else None


@router.put("/mood", response_model=MoodResponse)
def save_mood(payload: MoodInput, session: SessionDependency, user: CurrentUser) -> MoodResponse:
    return MoodResponse.model_validate(health_service.save_mood(session, user, payload))


@router.get("/mood/history", response_model=MoodHistoryResponse)
def mood_history(
    session: SessionDependency,
    user: CurrentUser,
    days: Annotated[int, Query()] = 7,
) -> MoodHistoryResponse:
    if days not in (7, 30):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Input should be 7 or 30.",
        )
    items = health_service.list_moods(session, user, days)
    return MoodHistoryResponse(items=items, days=days)


@router.post("/sleep", response_model=SleepResponse, status_code=status.HTTP_201_CREATED)
def log_sleep(payload: SleepInput, session: SessionDependency, user: CurrentUser) -> SleepResponse:
    return SleepResponse.model_validate(health_service.log_sleep(session, user, payload))


@router.get("/sleep", response_model=SleepListResponse)
def list_sleep(
    session: SessionDependency,
    user: CurrentUser,
    days: Annotated[int, Query(ge=1, le=30)] = 7,
) -> SleepListResponse:
    return SleepListResponse(items=health_service.list_sleep_logs(session, user, days))


@router.get("/habits", response_model=HabitListResponse)
def list_habits(session: SessionDependency, user: CurrentUser) -> HabitListResponse:
    habits, completed, weekly_counts, streaks = health_service.list_habits(session, user)
    return HabitListResponse(
        items=[
            _habit_response(
                habit,
                habit.id in completed,
                weekly_counts[habit.id],
                *streaks[habit.id],
            )
            for habit in habits
        ],
        total=len(habits),
    )


@router.post("/habits", response_model=HabitResponse, status_code=status.HTTP_201_CREATED)
def create_habit(
    payload: HabitInput, session: SessionDependency, user: CurrentUser
) -> HabitResponse:
    habit = health_service.create_habit(session, user, payload)
    return _habit_response(habit)


@router.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: UUID,
    payload: HabitInput,
    session: SessionDependency,
    user: CurrentUser,
) -> HabitResponse:
    habit = health_service.update_habit(session, user, habit_id, payload)
    _, completed, weekly_counts, streaks = health_service.list_habits(session, user)
    return _habit_response(
        habit,
        habit.id in completed,
        weekly_counts[habit.id],
        *streaks[habit.id],
    )


@router.post("/habits/{habit_id}/complete", response_model=HabitResponse)
def complete_habit(habit_id: UUID, session: SessionDependency, user: CurrentUser) -> HabitResponse:
    habit = health_service.complete_habit(session, user, habit_id)
    return _habit_response(
        habit,
        True,
        health_service.habit_weekly_count(session, user, habit),
        habit.current_streak,
        habit.longest_streak,
    )


@router.get("/water/today", response_model=WaterDayResponse)
def water_today(session: SessionDependency, user: CurrentUser) -> WaterDayResponse:
    log_date, total, goal, logs = health_service.get_water_today(session, user)
    return WaterDayResponse(
        log_date=log_date,
        total_ml=total,
        goal_ml=goal,
        items=[WaterLogResponse.model_validate(item) for item in logs],
    )


@router.post("/water", response_model=WaterLogResponse, status_code=status.HTTP_201_CREATED)
def add_water(
    payload: WaterInput, session: SessionDependency, user: CurrentUser
) -> WaterLogResponse:
    return WaterLogResponse.model_validate(health_service.add_water(session, user, payload))


@router.get("/today", response_model=dict[str, object])
def health_today(session: SessionDependency, user: CurrentUser) -> dict[str, object]:
    mood = health_service.get_mood_today(session, user)
    log_date, total, goal, _ = health_service.get_water_today(session, user)
    habits, completed, _, _ = health_service.list_habits(session, user)
    return {
        "date": log_date,
        "mood_score": mood.mood_score if mood else None,
        "water_total_ml": total,
        "water_goal_ml": goal,
        "habits_completed": len(completed),
        "habits_total": len(habits),
    }
