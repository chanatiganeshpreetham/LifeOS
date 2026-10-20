from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.daybook import router as daybook_router
from app.routers.finance import router as finance_router
from app.routers.health import router as health_router
from app.routers.health_tracking import router as health_tracking_router
from app.routers.notes import router as notes_router
from app.routers.reminders import router as reminders_router
from app.routers.tasks import router as tasks_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(tasks_router)
api_router.include_router(reminders_router)
api_router.include_router(finance_router)
api_router.include_router(health_tracking_router)
api_router.include_router(notes_router)
api_router.include_router(daybook_router)
