---
name: "LifeOS 01 - Project Foundation"
description: "Create only the approved LifeOS development foundation: app skeletons, local services, migrations, health check, and CI."
argument-hint: "Approved Phase 0 decisions or a specific foundation task"
agent: "agent"
---

Implement the LifeOS project foundation only. First inspect the workspace and read [the SRS](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx), [technical architecture](../../Life%20os%20personal%20plan/LifeOS_Technical_Architecture_Phase1.docx), [Phase 1 DBML](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml), and the approved decisions/backlog from `/00-lifeos-review-and-plan`. If scope decisions have not been approved, stop and ask before coding.

Scope:
- Establish a maintainable React 18 + TypeScript web client using currently maintained, security-patched Vite and Tailwind releases, responsive from 375px upward, with React Router and TanStack Query. If source documents pin a vulnerable version, prefer the closest secure compatible release and document the deviation.
- Establish a Python 3.12 FastAPI backend using Pydantic v2, SQLAlchemy 2 in sync mode for Phase 1, Alembic, PostgreSQL 16, and a cleanly separated service/repository structure.
- Add Docker Compose local development services for the API and optional local email testing. Use the configured Prisma Postgres database directly; do not add a local PostgreSQL, Redis, or Celery service.
- Add safe configuration loading with `.env.example`, a minimal health endpoint, an initial empty Alembic migration setup, and focused CI for Python lint/test and frontend lint/test/build.
- Add only foundation-level shared layout, responsive shell, and API wiring needed to prove the client talks to the backend. Do not implement product modules or real authentication yet.

Requirements:
- Follow the existing workspace conventions when present; do not overwrite or delete existing files to impose a preferred scaffold.
- Keep secrets out of source control. Required production configuration must fail clearly at startup; provide safe development-only defaults only where appropriate.
- Keep API routes versioned under `/api/v1`; document the health endpoint and startup commands.
- Use a migration framework from the start; no ad-hoc schema changes.
- Add a concise README or update the existing one with prerequisites, environment setup, startup, migrations, checks, and service URLs.
- Verify the exact foundation outcome: compose services start, API health returns success, Alembic is usable, and client lint/tests/build plus backend lint/tests pass (or report specific environment blockers).
- Do not add unrelated infrastructure, production deployment, product tables, PWA installability, or offline caching.

At completion, summarize changed files, commands run and results, and any blockers. Stop at this stage; do not begin auth or product features.
