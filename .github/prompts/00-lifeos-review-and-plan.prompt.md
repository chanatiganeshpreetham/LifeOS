---
name: "LifeOS 00 - Review Requirements and Plan"
description: "Use first for LifeOS: inspect the plan documents, reconcile open decisions, and produce an approved implementation sequence without changing code."
argument-hint: "Optional focus area or decisions already made"
agent: "agent"
---

Review the LifeOS project before implementation. This is a requirements and planning task only: do not create or modify application code, configuration, or schema.

Read the source documents in [the personal plan folder](../../Life%20os%20personal%20plan/):
- [LifeOS SRS v1.0](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx)
- [Phase 1 technical architecture](../../Life%20os%20personal%20plan/LifeOS_Technical_Architecture_Phase1.docx)
- [Phase 1 schema](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml)

Also inspect the current workspace, its git state if available, installed/runtime constraints, and any existing code or project instructions. The workspace may be empty; verify rather than assume.

Treat the documents as the product source of truth, but call out conflicts instead of choosing silently. In particular, verify and report:
- The SRS is a draft awaiting sign-off.
- Phase 1 overviews/build-order differ on whether subscriptions and the lite relationship CRM belong in MVP.
- The SRS security wording about where JWTs are stored must be reconciled with its detailed auth flow and the architecture, which describe an access token held in memory and an opaque refresh token in an HttpOnly cookie.
- A responsive web app/mobile browser experience is in scope; native iOS/Android apps are out of scope. PWA installability/offline caching are later-phase items, while browser push is a Phase 1 feature.
- The DBML is a design reference, not permission to add every Phase 2/3 table or feature to the MVP. Verify schema details and constraints before proposing migrations.

Produce a concise but sufficiently detailed report with:
1. What exists in the workspace and what is missing.
2. Product scope and Phase 1 acceptance criteria, organized by module.
3. The agreed technical baseline from the documents: React 18/Vite/Tailwind, mobile-responsive web, FastAPI/Python 3.12, SQLAlchemy 2, Alembic, PostgreSQL 16, Redis 7/Celery 5 as applicable, Docker Compose, and CI.
4. Important architecture/data/security invariants, including per-user data scoping, UUID keys, `NUMERIC(12,2)` money, ORM parameterization, migrations-only schema changes, no tokens in localStorage, explicit CORS, validation, and test expectations.
5. Contradictions, ambiguities, and decisions that need the product owner’s answer. Rank them by impact and ask focused questions only where needed.
6. A dependency-ordered, small-step implementation backlog with a verifiable definition of done for each step. Follow the architecture’s sequence: foundation, auth, tasks, reminders/push, finance and card dates, health/notes and the remaining approved Phase 1 modules, then dashboard integration and release hardening. Keep optional/later-phase work out.

Do not implement anything until the product owner confirms the scope and answers any blocking decisions. Make no unverified assumptions, and distinguish document requirements from your recommendations.
