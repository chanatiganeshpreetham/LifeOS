---
name: "LifeOS 04 - Reminders and Push"
description: "Implement LifeOS reminders, in-app notifications, and browser push delivery using the shared scheduled-job design."
argument-hint: "Optional reminder behavior or notification surface"
agent: "agent"
---

Implement reminders and browser push only, after the foundation and authentication stages. Read the reminder/notification requirements in the [SRS](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx), the reminder and notification table definitions in the [Phase 1 DBML](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml), and the Celery/Web Push design in the technical architecture. Follow decisions approved in `/00-lifeos-review-and-plan`.

Deliver the approved Phase 1 behavior:
- User-scoped reminder CRUD, one-time and documented recurring schedules, acknowledgement, and approved snooze intervals.
- An in-process API scheduler for due reminders with correct timezone handling and duplicate-delivery protection; avoid external brokers and worker services.
- Web Push subscription registration and delivery using VAPID/pywebpush only when configured; permission denial or unsupported browsers must leave in-app reminders usable and show a clear state.
- In-app notification list/bell, unread count, and mark-read behavior using the shared notification log model.
- Responsive reminder and notification UI with loading, empty, error, and permission states.

Security/reliability:
- Do not store VAPID private keys in the repository or send private material to clients. Validate subscription ownership and payloads.
- Make delivery idempotent and handle expired/invalid subscriptions explicitly; log operational failures without silently presenting them as successful delivery.
- Respect user timezone and recurrence rules; avoid polling/query patterns that can send duplicates.
- Use the existing Celery/Redis pattern and Alembic migrations; do not introduce another scheduler or notification subsystem.
- PWA installability/offline cache are later-phase scope. Implement only the service-worker behavior required for the approved Phase 1 browser push experience.

Test reminder scheduling, timezone boundaries, recurrence/snooze, ownership isolation, acknowledgement/unread counts, duplicate prevention, and push failure/unsupported-browser handling. Run focused tests, lint, migrations, and client build. Summarize changed files, verification, environment settings still required, and blockers; do not start finance.
