---
name: "LifeOS 03 - Task Manager"
description: "Implement the LifeOS Phase 1 task manager with user-scoped CRUD, filters, search, and approved recurring-task behavior."
argument-hint: "Optional task feature or acceptance criterion"
agent: "agent"
---

Implement the task-manager stage only, after foundation and authentication are complete. Inspect existing patterns and read the task requirements/build order in the [SRS](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx), task/recurring-rule definitions in the [Phase 1 DBML](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml), and task architecture in the technical architecture document. Honor the approved scope from `/00-lifeos-review-and-plan`; recurring tasks are only in this stage if their Phase 1 scope is confirmed.

Deliver the approved Phase 1 task capabilities end-to-end:
- Create, read, update, complete/uncomplete, and soft-delete tasks.
- Priorities, due date/time, notes, and the specified All/Today/Overdue/Completed filters.
- Full-text keyword search using PostgreSQL `tsvector`/GIN only where specified and supported by correct migration/trigger behavior.
- Responsive task list and quick capture, with loading, empty, validation, and error states.
- Recurring task rules and scheduled generation only if approved for the current MVP; generation must be idempotent and timezone-aware.

All reads and writes must be scoped to the authenticated user, including lookup-by-ID and search. Validate ownership and inputs; use SQLAlchemy parameterized queries, Alembic migrations, and service/repository boundaries. Honor soft deletion and avoid exposing deleted rows. Never build project grouping, subtasks, calendar sync, drag-and-drop, or other later-phase features unless explicitly approved.

Add focused API/service/UI tests for CRUD, ownership isolation, filters (including date/timezone boundaries), search, completion, deletion, and recurring generation if included. Run relevant tests, lint, migrations, and client build. Report changed files, verification results, and remaining work; do not start reminders or finance.
