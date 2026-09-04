# R.AI Architecture

R.AI is intended to become an autonomous revenue recovery platform for merchants, but Sprint 1 only establishes the foundation. The current application includes a frontend shell, FastAPI backend, PostgreSQL persistence, an initial Merchant model, migrations, and tests.

## Future Operating Model

```text
R.AI Orchestrator
-> Diagnosis
-> Strategy
-> Policy Engine
-> Action Executor
-> Payment Provider
-> Audit
```

The orchestrator may coordinate future analysis and recovery workflows. Diagnosis and strategy layers may use AI-generated reasoning or structured outputs in later sprints. The Policy Engine must remain deterministic application code. The Action Executor must be bounded by policy, idempotency, approval requirements, and stopping conditions.

**The LLM will never have unrestricted authority over payment operations.**

## Sprint 1 Boundaries

Sprint 1 does not include Razorpay integration, payment execution, autonomous retries, payment reminders, subscription recovery, LLM calls, fraud detection, advanced analytics, notifications, billing, or production authentication.

## Current Components

- `apps/web`: Next.js App Router frontend with an operations dashboard shell and route placeholders.
- `apps/api`: FastAPI application with configuration, database session management, Merchant model, Alembic migration, and health endpoint.
- `postgres`: PostgreSQL database used by Docker Compose.

## Data Model

Sprint 1 includes only the `Merchant` model:

- `id`: UUID primary key
- `name`: merchant display name
- `email`: merchant contact email
- `created_at`: timezone-aware creation timestamp
- `updated_at`: timezone-aware update timestamp

Future payment, recovery, audit, and policy tables should be added only when their sprint explicitly calls for them.
