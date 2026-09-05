# R.AI Project Context

This document preserves product state and roadmap for coding agents. Engineering rules live in `AGENTS.md`. Do not treat this file as a substitute for that constitution.

## What R.AI is

R.AI (Revenue AI) is a Razorpay AI Buildathon project: an autonomous revenue recovery platform for merchants. The intended operating loop is:

1. Payment event
2. Diagnosis
3. Recoverability assessment
4. Recovery strategy
5. Deterministic policy validation
6. Bounded execution
7. Outcome observation
8. Audit trail
9. Evaluation

The LLM must never have unrestricted authority over payment operations. The Policy Engine must remain deterministic application code.

## Current sprint

**Sprint 2 — Payment & Recovery Intelligence** (in progress at the time this file was created; update the completed-state section after verification).

Sprint 1 foundation is already implemented and must not be rebuilt.

## Completed Sprint 1 functionality

- Monorepo layout (`apps/web`, `apps/api`, `docs`, `scripts`, `data`)
- Next.js App Router frontend with Tailwind dashboard shell
- FastAPI backend with health endpoint
- PostgreSQL, SQLAlchemy 2.x, Alembic
- Merchant model and initial migration
- Docker Compose for web, api, and postgres
- Centralized frontend API client
- Backend tests and frontend lint/typecheck scripts
- README and architecture documentation

Sprint 1 dashboard Payments/Recovery routes were shells with mock or placeholder content.

## Current technology stack

- Frontend: Next.js, TypeScript, App Router, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic
- Database: PostgreSQL 16
- Infrastructure: Docker, Docker Compose

## Repository structure

```text
apps/web          Next.js operations UI
apps/api          FastAPI service, models, migrations, tests
apps/api/app/recovery   Deterministic recovery intelligence (Sprint 2)
data              Raw / generated / evaluation datasets
docs              Architecture and agent handoff
scripts           Developer workflows (seed/generate)
```

## Important architectural decisions

- Layering: API routes stay thin; domain logic lives in services/recovery modules.
- Frontend data access goes through `apps/web/src/lib/api-client.ts`.
- UUID primary keys and timezone-aware timestamps.
- Payment-provider integrations stay behind an abstraction when they exist; Sprint 2 has no provider.
- Mock and test behavior must work without external credentials.

## Important safety constraints

- No real payment execution.
- No Razorpay API calls in Sprint 2.
- No LLM or agent framework in Sprint 2.
- No autonomous payment actions.
- Future LLM proposals must be validated by deterministic policy code before any action.
- High-risk actions will require human approval in later sprints.
- Never commit secrets.

## Current Docker / runtime setup

Expected local ports:

- Frontend: `3000`
- Backend: `8000`
- PostgreSQL: `5432`

Compose services: `web`, `api`, `postgres` (volume `postgres_data`).

API health: `GET /health`.

Copy `.env.example` to `.env` for local overrides. Do not commit filled `.env` files with secrets.

## What remains to be built (after Sprint 2)

- LLM-assisted diagnosis and strategy (bounded, structured, validated)
- Deterministic policy engine with approval gates
- Bounded action executor
- Payment provider abstraction and Razorpay test-mode integration
- Audit trail for autonomous actions
- Evaluation harness
- Production authentication, notifications, billing, fraud detection, advanced analytics

## Sprint 2 objective

Build the deterministic data and domain substrate for future AI agents:

- Customer, Payment, PaymentFailure, Subscription, RecoveryCase models
- Alembic migration
- Deterministic synthetic data generation
- Recoverability scoring, eligibility, suggested actions
- Idempotent recovery-case analysis
- Payments, recovery cases, summary, and analyze APIs
- Dashboard / Payments / Recovery pages backed by real API data
- Meaningful automated tests

Explicitly out of scope for Sprint 2: LLM, agents, Razorpay, real charges, autonomous retries.

## Future sprint roadmap

Recommended next sprint only after Sprint 2 is complete:

**Sprint 3 — Diagnosis & policy foundation (no execution)**

- Structured diagnosis records for failed payments
- Deterministic policy engine (retry limits, high-value thresholds, approval requirements, stop conditions, idempotency keys)
- Compare baseline strategy vs a future AI-proposed strategy without executing payments
- Audit log schema for proposed vs permitted actions

Later sprints can add provider tools, bounded execution in test mode, evaluation, and operator approval workflows.
