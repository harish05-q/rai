# R.AI

R.AI is a Revenue AI foundation for merchant revenue intelligence and recovery. Sprint 1 establishes the production-grade monorepo base only: frontend shell, backend service, PostgreSQL persistence, migrations, tests, Docker Compose, and documentation.

No Razorpay calls, real payment execution, LLM calls, autonomous recovery, notifications, or production authentication are implemented in this sprint.

## Architecture Overview

```text
apps/web  -> Next.js dashboard and operations shell
apps/api  -> FastAPI service, configuration, database models, migrations
postgres  -> PostgreSQL persistence for application data
docs      -> Architecture notes and sprint documentation
```

The backend owns persistence and health checks. The frontend consumes backend APIs through a centralized API client so future product data can move behind typed service boundaries without scattering `fetch` calls through UI components.

## Repository Structure

```text
apps/
  api/
    alembic/
    app/
    tests/
  web/
    src/
data/
  raw/
  generated/
  evaluation/
docs/
scripts/
docker-compose.yml
```

## Prerequisites

- Node.js 22+
- npm 10+
- Python 3.12+
- Docker Desktop with Docker Compose
- PostgreSQL for local non-Docker database runs

## Environment Setup

Copy the example environment file and adjust values for your machine:

```bash
cp .env.example .env
```

For local development outside Docker, set `DATABASE_URL` to a PostgreSQL database reachable from your host, for example:

```text
DATABASE_URL=postgresql+psycopg://rai:rai_dev_password@localhost:5432/rai
```

Do not commit real secrets or credentials.

## Running Locally

Install frontend dependencies:

```bash
cd apps/web
npm install
npm run dev
```

Install backend dependencies:

```bash
cd apps/api
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The web app runs at `http://localhost:3000`. The API runs at `http://localhost:8000`.

## Running With Docker Compose

From the repository root:

```bash
docker compose up --build
```

Services:

- `web`: Next.js app on `http://localhost:3000`
- `api`: FastAPI app on `http://localhost:8000`
- `postgres`: PostgreSQL with persistent volume `postgres_data`

## Running Migrations

Inside `apps/api` with dependencies installed:

```bash
alembic upgrade head
```

In Docker:

```bash
docker compose run --rm api alembic upgrade head
```

The initial migration creates the `merchants` table with UUID primary keys and timezone-aware timestamps.

## Testing

Backend:

```bash
cd apps/api
pytest
```

Frontend:

```bash
cd apps/web
npm run lint
npm run typecheck
```

## Current Sprint 1 Scope

Implemented in this sprint:

- Monorepo structure
- Next.js TypeScript frontend with App Router and Tailwind CSS
- FastAPI backend
- PostgreSQL configuration
- Docker Compose
- Environment configuration
- Initial Merchant model and Alembic migration
- Health endpoint
- Initial dashboard shell with mock data
- Backend tests and frontend static checks
- Developer documentation

Explicitly out of scope:

- Razorpay integration
- Real payment execution
- Autonomous agents
- LLM integration
- Recovery algorithms
- Fraud detection
- Advanced analytics
- Production authentication
- Notifications
- Billing

## Planned Future Architecture

Future sprints can evolve toward:

```text
R.AI Orchestrator
-> Diagnosis
-> Recovery Strategy
-> Deterministic Policy Engine
-> Bounded Action Executor
-> Payment Provider Tools
-> Audit
```

The LLM will never have unrestricted authority over payment operations. It may propose actions in a future sprint; deterministic application code must decide whether an action is permitted.
