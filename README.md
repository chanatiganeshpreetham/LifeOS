# LifeOS

LifeOS is a personal life-management application. The first release targets a responsive web experience, including mobile browsers; native iOS/Android apps and offline PWA behavior are not part of the MVP.

The implementation follows the approved P1-focused MVP boundary. P2 items and the subscriptions/contacts modules are deferred unless a later product decision brings them into scope. The planning documents remain the requirements reference:

- [Software Requirements Specification](./Life%20os%20personal%20plan/LifeOS_SRS_v1.0.docx)
- [Phase 1 Technical Architecture](./Life%20os%20personal%20plan/LifeOS_Technical_Architecture_Phase1.docx)
- [Phase 1 DBML reference](./Life%20os%20personal%20plan/lifeos_phase1_schema.dbml)

The frontend build-tool versions are newer than the original April 2025 architecture document to avoid known vulnerabilities in its pinned Vite 5 and Tailwind CSS 3 dependency trees.

## Stack

- Frontend: React 18, TypeScript, Vite 6, Tailwind CSS 4, React Router 6, TanStack Query 5
- Backend: Python 3.12, FastAPI, Pydantic 2, synchronous SQLAlchemy 2, Alembic, pure-Python pg8000 PostgreSQL driver
- Database: Prisma Postgres
- Local email testing: Mailpit
- Local development: Docker Compose

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js 20 or newer and npm
- Python 3.12 (only needed to run backend commands directly on the host; Docker uses Python 3.12)

For backend work directly on the host, create and activate a virtual environment from the project root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

## Local setup

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
# Set DATABASE_URL in .env to your Prisma Postgres connection URL before continuing.
docker compose up --build
```

The API (which applies Alembic migrations to the configured Prisma Postgres database at startup) and Mailpit for local email testing start in Compose. Scheduled reminders, finance alerts, and pending browser push notifications run inside the API process, so no Redis server or worker services are required. Run the frontend separately:

```powershell
Copy-Item frontend\.env.example frontend\.env.local
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

The frontend is served at <http://localhost:5173>. The Vite development proxy forwards `/api` requests to FastAPI on port 8000. The API health endpoint is <http://localhost:8000/api/v1/health>; interactive API documentation is at <http://localhost:8000/docs>. In Compose mode, Mailpit is available at <http://localhost:8025> for other backend email notifications.

The local app serves on `http://localhost:5173`. Auth0 Universal Login handles sign-in, sign-up, and password recovery. In the Auth0 application's settings, add `http://localhost:5173` to **Allowed Callback URLs**, **Allowed Logout URLs**, and **Allowed Web Origins**. Keep any other existing URLs in those fields; separate URLs with commas. Auth0 treats `localhost` and `127.0.0.1` as different callback URLs.

### Production deployment on Ubuntu with existing PostgreSQL and Nginx

The production Compose stack builds the API and static frontend images. It binds the frontend to `127.0.0.1:8080`; the included Nginx site file is a template for the host's Nginx and proxies traffic to that port. The API is reachable only from the Docker network. PostgreSQL remains on the host.

From the cloned repository on the VPS:

```bash
cp .env.production.example .env.production
nano .env.production
```

Set the domain, Auth0 values, a random `SECRET_KEY` of at least 32 characters, SMTP credentials, and a `DATABASE_URL` for the PostgreSQL role/database you created. For PostgreSQL on the VPS, use `host.docker.internal` as the hostname and make sure PostgreSQL accepts connections from the Docker bridge network. URL-encode reserved characters in credentials. Production startup requires SMTP configuration; without it the API refuses to start.

Build and start the stack:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f api
```

Copy `nginx/lifeos.conf` to `/etc/nginx/sites-available/lifeos`, replace `lifeos.example.com`, enable the site, and validate/reload Nginx. Then configure TLS for the domain with your certificate tooling and update the site to serve HTTPS. Auth0 must allow the production URL as a callback, logout URL, and web origin. After changing any `AUTH0_*` frontend values, rebuild the frontend image with the first command above.

The API applies Alembic migrations to your self-hosted PostgreSQL database before starting. Check `https://your-domain/api/v1/health` to confirm the database connection. The frontend health card also reports API and scheduled-job availability.

## Authentication

React obtains Auth0 access tokens for the LifeOS API. FastAPI verifies their RS256 signatures using the Auth0 tenant's JWKS, and checks issuer and audience before authorizing requests. On a user's first sign-in, the app sends the Auth0 ID token alongside the API access token to initialize their PostgreSQL profile; FastAPI independently verifies the ID token signature, issuer, client audience, and matching subject before using its profile claims. Existing local-password registration, login, email-verification, and password-reset API endpoints have been replaced; account recovery is handled by Auth0 Universal Login. Auth0 tokens are kept in the SDK's in-memory cache rather than browser local storage.

For host-based development without Docker, install Python 3.12 (Ubuntu 22.04's default Python is older), create a virtual environment, and install the backend dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Configure `.env` with a PostgreSQL URL for a database role you control, then run the migration from `backend`:

```bash
cd backend
python -m alembic upgrade head
```

On Linux, from the repository root, start the API and frontend in separate terminals:

```bash
cd backend
source ../.venv/bin/activate
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm ci
npm run dev
```

On Windows, use separate PowerShell terminals:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm.cmd run dev
```

## Database migrations

Product schema is introduced only through reviewed, versioned Alembic migrations; do not change an application schema manually.

```powershell
Set-Location backend
alembic upgrade head
alembic current
```

Run migrations only after the PostgreSQL service is available.

## Checks

Backend:

```powershell
Set-Location backend
..\.venv\Scripts\ruff.exe check .
..\.venv\Scripts\ruff.exe format --check .
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m alembic upgrade head --sql
```

Frontend:

```powershell
Set-Location frontend
npm.cmd ci
npm.cmd run lint
npm.cmd test -- --run
npm.cmd run build
```

GitHub Actions runs backend and frontend lint, tests, and the production frontend build on pushes and pull requests.

## Current foundation boundary

The authenticated Today dashboard summarizes pending and upcoming tasks, upcoming reminders, server-computed daily and monthly spend against an available monthly budget, card due dates within 30 days, and mood, sleep, habits, and water data. It uses independent authenticated queries with per-widget loading, retry, and empty states; dashboard tasks can be quick-added. Dashboard refreshes its module summaries every 60 seconds. Subscriptions, nutrition, AI digest, and CRM are not delivered and are intentionally not represented. The task manager supports user-scoped task CRUD, completion, soft deletion, All/Today/Overdue/Completed filters, timezone-aware due dates, and PostgreSQL full-text search. Reminders support one-time and recurring schedules, in-app notifications, and optional browser push. Finance supports manual INR expenses, default and personal categories, monthly and yearly plan-versus-actual summaries, category budgets with 80%/100% alerts, CSV export, and basic credit-card profiles with due-date notifications. Health includes timezone-aware mood check-ins, sleep duration logging, daily habit streaks, and water tracking; notes include debounced autosave and PostgreSQL full-text search. Daybook provides a calendar and private, date-based diary entries alongside linked task, reminder, finance, health, and note activity; the activity feed reads source records instead of copying them and refreshes periodically. P2 details such as reminder snooze, health annotations/charts, note tags and pinning remain deferred from the approved P1-focused MVP.

The task API is available under `/api/v1/tasks` (including `/dashboard` for compact dashboard task summaries); reminders and notification APIs are under `/api/v1/reminders` (including `/reminders/dashboard`), `/api/v1/notifications`, and `/api/v1/push`. Finance APIs are under `/api/v1/finance` (including `/dashboard-summary` for daily/monthly spend and upcoming card due dates); health tracking is under `/api/v1/health`, notes are under `/api/v1/notes`, and Daybook is under `/api/v1/daybook` (date-bounded activity feed plus diary-entry CRUD). These endpoints require a bearer access token. Apply database migrations after configuring PostgreSQL; revisions `0003_tasks`, `0004_reminders_push`, `0005_finance`, `0006_health_notes`, `0008_daybook`, and `0009_dashboard_task_index` add the corresponding product tables, indexes, and notification types.

### Prisma Postgres

Set `DATABASE_URL` in the ignored project-root `.env` to Prisma's direct PostgreSQL connection URL, including its `sslmode=require` option. URL-encode reserved characters in the username or password. Do not use a Prisma Accelerate `prisma://` URL. The API applies the schema on startup; to apply it manually:

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

### Reminder scheduler and browser push

The API runs due reminders, finance alerts, and pending browser push notifications in a background loop once per minute. Keep one API process running for these schedules; running multiple API processes can process the same scheduled work more than once. The `/api/v1/health` endpoint marks scheduled jobs healthy after a successful cycle and reports an error if cycles keep failing.

Browser push is optional. In development, `http://localhost` is a secure context for service workers. Generate VAPID values locally (the private value is secret):

```powershell
@'
from base64 import urlsafe_b64encode
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid

vapid = Vapid()
vapid.generate_keys()
private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
public_raw = vapid.public_key.public_bytes(
    serialization.Encoding.X962,
    serialization.PublicFormat.UncompressedPoint,
)
encode = lambda value: urlsafe_b64encode(value).rstrip(b"=").decode("ascii")
print("VAPID_PUBLIC_KEY=" + encode(public_raw))
print("VAPID_PRIVATE_KEY=" + encode(private_raw))
'@ | ..\.venv\Scripts\python.exe -
```

Copy those values into the ignored `.env`, and set `VAPID_CLAIMS_EMAIL` to the operator email address without a `mailto:` prefix. Keep the private key on the server only. Browser permission denial, unsupported push services, or missing VAPID configuration leave in-app reminders available.
