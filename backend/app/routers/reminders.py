from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.models import User
from app.schemas.reminder import (
    MessageResponse,
    NotificationListResponse,
    NotificationResponse,
    PushConfigResponse,
    PushSubscriptionInput,
    ReminderCreate,
    ReminderListResponse,
    ReminderResponse,
    ReminderUpdate,
)
from app.services import reminders as reminder_service

router = APIRouter(tags=["reminders"])
SessionDependency = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/reminders", response_model=ReminderListResponse)
def list_reminders(session: SessionDependency, user: CurrentUser) -> ReminderListResponse:
    items = reminder_service.list_reminders(session, user)
    return ReminderListResponse(items=items, total=len(items))


@router.get("/reminders/dashboard", response_model=ReminderListResponse)
def dashboard_reminders(session: SessionDependency, user: CurrentUser) -> ReminderListResponse:
    items = reminder_service.dashboard_reminders(session, user)
    return ReminderListResponse(items=items, total=len(items))


@router.post(
    "/reminders",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reminder(
    payload: ReminderCreate,
    session: SessionDependency,
    user: CurrentUser,
) -> ReminderResponse:
    return ReminderResponse.model_validate(reminder_service.create_reminder(session, user, payload))


@router.patch("/reminders/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: UUID,
    payload: ReminderUpdate,
    session: SessionDependency,
    user: CurrentUser,
) -> ReminderResponse:
    return ReminderResponse.model_validate(
        reminder_service.update_reminder(session, user, reminder_id, payload)
    )


@router.post("/reminders/{reminder_id}/acknowledge", response_model=ReminderResponse)
def acknowledge_reminder(
    reminder_id: UUID,
    session: SessionDependency,
    user: CurrentUser,
) -> ReminderResponse:
    return ReminderResponse.model_validate(
        reminder_service.acknowledge_reminder(session, user, reminder_id)
    )


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: UUID,
    session: SessionDependency,
    user: CurrentUser,
) -> None:
    reminder_service.delete_reminder(session, user, reminder_id)


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    session: SessionDependency,
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> NotificationListResponse:
    items, unread_count = reminder_service.get_notifications(session, user, limit)
    return NotificationListResponse(items=items, unread_count=unread_count)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    session: SessionDependency,
    user: CurrentUser,
) -> NotificationResponse:
    notification = reminder_service.mark_notification_read(session, user, notification_id)
    return NotificationResponse.model_validate(notification)


@router.post("/notifications/read-all", response_model=MessageResponse)
def mark_all_notifications_read(session: SessionDependency, user: CurrentUser) -> MessageResponse:
    reminder_service.mark_all_notifications_read(session, user)
    return MessageResponse(message="All notifications marked as read.")


@router.get("/push/config", response_model=PushConfigResponse)
def push_config(user: CurrentUser) -> PushConfigResponse:
    enabled, public_key = reminder_service.get_push_config()
    return PushConfigResponse(enabled=enabled, public_key=public_key)


@router.put("/push/subscription", status_code=status.HTTP_204_NO_CONTENT)
def register_push_subscription(
    payload: PushSubscriptionInput,
    session: SessionDependency,
    user: CurrentUser,
) -> None:
    settings = get_settings()
    if not settings.vapid_claims_email or "@" not in settings.vapid_claims_email:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Browser push is not configured on this server. In-app reminders remain available."
            ),
        )
    reminder_service.upsert_push_subscription(
        session,
        user,
        str(payload.endpoint),
        payload.p256dh_key,
        payload.auth_key,
        payload.device_label,
    )


@router.delete("/push/subscription", response_model=MessageResponse)
def unregister_push_subscription(
    endpoint: Annotated[str, Query(min_length=10, max_length=2048)],
    session: SessionDependency,
    user: CurrentUser,
) -> MessageResponse:
    reminder_service.remove_push_subscription(session, user, endpoint)
    return MessageResponse(message="Browser push subscription removed.")
