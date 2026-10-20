---
name: "LifeOS 05 - Expenses and Credit Cards"
description: "Implement the approved LifeOS Phase 1 finance scope: expenses, categories, budgets, income, and card due dates."
argument-hint: "Optional finance module or acceptance criterion"
agent: "agent"
---

Implement the approved finance stage only, after foundation, authentication, and the shared notification infrastructure are complete. Read the finance and credit-card requirements in the [SRS](../../Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx), related table definitions in the [Phase 1 DBML](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml), and approved decisions/backlog from `/00-lifeos-review-and-plan`.

Implement only confirmed Phase 1 features:
- Expense categories (including the approved system defaults and custom categories), manual expense entry, history filters/sorting, and CSV export.
- Monthly category budgets and 80%/100% alerts if confirmed in MVP; ensure alert thresholds and reset behavior are correct and do not duplicate notifications.
- Income entries if confirmed in MVP.
- Credit-card details, due-date countdown, and scheduled reminders/alerts if confirmed in MVP. Never collect/store a full card number or CVV; keep only the documented minimal metadata.
- Responsive finance and card pages, forms, charts where approved, and explicit loading/empty/error states.
- Also like monthly income how much how much you plan to save invest , spend loans and max budget to spend in a month and how much you have spent and how much you have left to spend in a month and how much you have saved and how much you have invested and how much you have borrowed and how much you have to pay back in a month and how much you have to pay back in a year
Financial correctness and data isolation are mandatory:
- Store all money as PostgreSQL `NUMERIC(12,2)`/Python `Decimal`; never use floating-point arithmetic for amounts. Default currency is INR as specified.
- Scope every query and mutation to the authenticated user; validate category/card ownership and soft-delete behavior.
- Use ORM parameters, Pydantic validation, service/repository boundaries, Alembic migrations, and the shared notification service.
- Make CSV output UTF-8 and protect spreadsheet consumers from formula injection.
- Do not implement SMS parsing, bank integrations, reward optimization, utilization analytics, net worth, or other later-phase features.

Add focused tests for decimal arithmetic, budgets/threshold boundaries, monthly rollover, date filters, CSV escaping/encoding, ownership isolation, card due-date boundaries, and alert idempotency for included features. Run tests, lint, migrations, and client build; summarize changed files, results, and remaining decisions. Do not start health, notes, subscriptions, or CRM.
