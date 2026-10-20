from datetime import UTC, datetime

from app.db.session import SessionLocal
from app.services.finance import dispatch_finance_alerts
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.finance_tasks.dispatch_finance_alerts")
def run_finance_alerts() -> int:
    with SessionLocal() as session:
        return dispatch_finance_alerts(session, datetime.now(UTC))
