# R.AI

R.AI is a Revenue AI platform for merchant revenue intelligence and recovery. Sprint 2 adds deterministic payment and recovery intelligence on top of the Sprint 1 foundation.

No Razorpay calls, real payment execution, LLM calls, or autonomous recovery actions are implemented.

## Architecture Overview

```text
apps/web  -> Next.js dashboard (payments, recovery, summary KPIs)
apps/api  -> FastAPI service, domain models, recovery intelligence
postgres  -> PostgreSQL persistence
docs      -> Architecture, project context, scoring notes
scripts   -> Synthetic data generation and demo seed
```

The frontend consumes backend APIs only through `apps/web/src/lib/api-client.ts`.

## Synthetic data

All generated customers are fake (`@example.invalid`). Generation uses a fixed seed.

From the repository root (API dependencies installed, `DATABASE_URL` set):

```bash
python scripts/generate_data.py --seed 42 --customers 1000 --payments 10000
python scripts/seed_demo.py
```

`seed_demo.py` generates data and runs deterministic recovery analysis. It does not execute payments.

In Docker, after migrations:

```bash
docker compose exec api python -m app.data.seed
```

## Running migrations

```bash
cd apps/api
alembic upgrade head
```

In Docker:

```bash
docker compose run --rm api alembic upgrade head
```

Sprint 1 created `merchants`. Sprint 2 adds `customers`, `payments`, `payment_failures`, `subscriptions`, and `recovery_cases`.

## API

- `GET /health`
- `GET /api/v1/payments`
- `GET /api/v1/recovery/cases`
- `GET /api/v1/recovery/summary`
- `POST /api/v1/recovery/analyze` — scores failed payments; never charges or retries

## Testing

```bash
cd apps/api
pytest
```

```bash
cd apps/web
npm run lint
npm run typecheck
```

Scoring formula and eligibility rules: `docs/recovery-intelligence.md`. Agent handoff: `docs/PROJECT_CONTEXT.md`.

## Current Sprint 2 scope

Implemented:

- Customer, Payment, PaymentFailure, Subscription, RecoveryCase models
- Deterministic recoverability scoring, eligibility, and baseline suggested actions
- Idempotent recovery-case analysis
- Synthetic dataset (1,000 customers / 10,000 payments)
- Dashboard, Payments, and Recovery pages backed by the API

Explicitly out of scope:

- Razorpay integration
- Real payment execution
- Autonomous agents
- LLM integration
- Fraud detection
- Advanced analytics
- Production authentication
- Notifications
- Billing

## Planned future architecture

```text
R.AI Orchestrator
-> Diagnosis
-> Recovery Strategy
-> Deterministic Policy Engine
-> Bounded Action Executor
-> Payment Provider Tools
-> Audit
```

The LLM will never have unrestricted authority over payment operations.
