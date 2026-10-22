from app.services import scheduler


def test_scheduled_cycle_runs_reminders_and_finance_alerts(monkeypatch) -> None:
    processed: list[str] = []
    monkeypatch.setattr(scheduler, "_deliver_reminders", lambda: processed.append("reminders") or 2)
    monkeypatch.setattr(
        scheduler,
        "_dispatch_finance_alerts",
        lambda: processed.append("finance") or 1,
    )

    assert scheduler.run_scheduled_jobs() is True
    assert processed == ["reminders", "finance"]


def test_scheduled_cycle_continues_after_a_job_fails(monkeypatch) -> None:
    processed: list[str] = []

    def fail_reminders() -> int:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(scheduler, "_deliver_reminders", fail_reminders)
    monkeypatch.setattr(
        scheduler,
        "_dispatch_finance_alerts",
        lambda: processed.append("finance") or 1,
    )

    assert scheduler.run_scheduled_jobs() is False
    assert processed == ["finance"]
