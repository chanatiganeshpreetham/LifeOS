---
name: "LifeOS 06 - Health and Notes"
description: "Implement the approved LifeOS Phase 1 mood, sleep, habit, water, and notes capabilities."
argument-hint: "Optional health or notes feature"
agent: "agent"
---

Implement the approved health and notes stage only, after foundation and authentication. Read relevant SRS requirements, the corresponding definitions in the [Phase 1 DBML](../../Life%20os%20personal%20plan/lifeos_phase1_schema.dbml), architecture notes, and `/00-lifeos-review-and-plan`. Inspect existing APIs/UI and reuse shared patterns.

Implement only approved Phase 1 scope:
- Mood check-in (score 1–5, optional note if included) and 7-/30-day history as specified.
- Sleep logging with server-calculated duration, quality and sleep-date attribution rules; do not trust client-computed duration.
- Habits, daily completion, and current/longest streak logic; enforce one completion per habit/date and preserve longest streak.
- Water tap-to-add (250 ml default) and daily totals/goal.
- Notes create/edit, debounce autosave, full-text search, and tags only if confirmed Phase 1.
- Accessible responsive UI with empty/loading/error states and validation.

All health and personal data must be scoped to the signed-in user; verify ownership for every lookup and write. Use database constraints/migrations for uniqueness where appropriate, transactions for related updates, and service/repository separation. Respect user timezone for day boundaries and streaks. Avoid treating mood data as clinical advice. Do not build food logging, workouts, journal/AI, sleep analytics, habit heatmaps, or later-phase features.

Add focused tests for daily uniqueness/upsert behavior, timezone boundaries, sleep duration/date calculations (including overnight sleep), habit streak edge cases and longest-streak preservation, water aggregation, note autosave/search/tags where included, and ownership isolation. Run relevant tests, lint, migrations, and client build. Summarize changes and verification; do not begin subscriptions or CRM.
