import asyncio
import logging
import time
from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.services.finance import dispatch_finance_alerts
from app.services.reminders import deliver_due_reminders

logger = logging.getLogger(__name__)
_SCHEDULE_INTERVAL_SECONDS = 60
_HEALTH_MAX_AGE_SECONDS = _SCHEDULE_INTERVAL_SECONDS * 2 + 5
_last_successful_cycle: float | None = None


def is_scheduler_healthy() -> bool:
    return (
        _last_successful_cycle is not None
        and time.monotonic() - _last_successful_cycle <= _HEALTH_MAX_AGE_SECONDS
    )


def run_scheduled_jobs() -> bool:
    all_succeeded = True
    jobs = (
        ("due reminders and pending push notifications", _deliver_reminders),
        ("finance alerts", _dispatch_finance_alerts),
    )
    for name, job in jobs:
        try:
            processed = job()
            logger.info("Scheduled %s job completed; processed %s item(s)", name, processed)
        except Exception:
            all_succeeded = False
            logger.exception("Scheduled %s job failed", name)
    return all_succeeded


def _deliver_reminders() -> int:
    with SessionLocal() as session:
        return deliver_due_reminders(session)


def _dispatch_finance_alerts() -> int:
    with SessionLocal() as session:
        return dispatch_finance_alerts(session, datetime.now(UTC))


async def run_scheduler() -> None:
    global _last_successful_cycle

    while True:
        if await asyncio.to_thread(run_scheduled_jobs):
            _last_successful_cycle = time.monotonic()
        else:
            _last_successful_cycle = None
        await asyncio.sleep(_SCHEDULE_INTERVAL_SECONDS)
