---
name: "LifeOS 08 - Dashboard and Phase 1 Release"
description: "Integrate completed LifeOS Phase 1 modules into the dashboard, verify mobile responsiveness, and close release-quality gaps."
argument-hint: "Optional dashboard widget or release acceptance criterion"
agent: "agent"
---

Implement dashboard integration and Phase 1 release hardening only after all approved Phase 1 modules are complete and individually verified. Read the dashboard and non-functional requirements in the [SRS](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx), architecture performance/release requirements, current module implementations, and the approved Phase 1 backlog.

Dashboard work:
- Build the dashboard last, using real authenticated APIs for only the modules actually delivered. Do not invent/mock unavailable Phase 1 features.
- Implement approved summary cards/widgets: current tasks, daily spend vs budget where budget scope exists, upcoming reminders, credit-card due dates, and any approved mood/sleep/habit/water/subscription summaries.
- Keep calculations server-authoritative where they aggregate personal data; user-scope all queries and define timezone/date boundaries explicitly.
- Use TanStack Query and existing API patterns; provide skeleton/loading, empty, error, and retry states per widget.
- Make each widget navigate to its module and ensure mobile layout is usable at 375px, tablet at 768px, and desktop.

Release verification:
- Check Phase 1 acceptance criteria against the approved backlog; fix only issues directly blocking those criteria.
- Verify API error responses do not expose stack traces/secrets, CORS is explicit, migrations work from a clean database, and no credentials are committed.
- Run relevant/full project tests, backend/frontend lint and formatting checks, production client build, and migration checks. Address failures caused by this work.
- Verify documented local startup and required environment variables, and update README/architecture notes for actual behavior, commands, and known omissions.
- Measure dashboard performance against the documented targets where the local environment allows; report measured results and limitations rather than claiming unmeasured success.

Do not add Phase 2/3 functionality (AI, native apps, offline PWA, OAuth, 2FA, integrations, or unapproved modules). Report a requirement-by-requirement acceptance checklist, exact verification commands/results, known gaps, and recommended next step. Do not deploy or perform destructive database operations unless explicitly requested.
