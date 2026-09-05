# R.AI Architecture

R.AI is intended to become an autonomous revenue recovery platform for merchants. Sprint 1 established the foundation. Sprint 2 adds the deterministic payment and recovery domain used as a baseline for future AI strategy.

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

The Policy Engine must remain deterministic application code. The Action Executor must be bounded by policy, idempotency, approval requirements, and stopping conditions.

**The LLM will never have unrestricted authority over payment operations.**

## Sprint 2 Boundaries

Sprint 2 does not include Razorpay integration, payment execution, autonomous retries, LLM calls, fraud detection, advanced analytics, notifications, billing, or production authentication.

`POST /api/v1/recovery/analyze` only writes recovery cases. It must never call a payment provider.

## Current Components

- `apps/web`: Next.js App Router frontend. Dashboard, Payments, and Recovery read API data through the shared client.
- `apps/api`: FastAPI application with Merchant plus payment/recovery models, recovery intelligence, and list/analyze endpoints.
- `apps/api/app/recovery`: scoring, eligibility, constants, and analysis service.
- `postgres`: PostgreSQL database used by Docker Compose.

## Data Model

- `Merchant`: Sprint 1 tenant record
- `Customer`: merchant-scoped synthetic payer with payment aggregates
- `Payment`: amount, method, status, attempt, checkout flags
- `PaymentFailure`: failure code, category, message, occurred_at
- `Subscription`: plan, amount, status, next billing
- `RecoveryCase`: one case per payment (unique `payment_id`), score, eligibility, suggested action, status

UUID primary keys and timezone-aware timestamps are used throughout. Scoring details are in `docs/recovery-intelligence.md`.
