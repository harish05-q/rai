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

**Sprint 4 — Guardrails + Action Execution + Razorpay integration** is complete.

Sprints 1–3 remain in place and were not rebuilt.

Do not start Sprint 5 automatically.

## Completed functionality

### Sprint 1

- Monorepo, Next.js, FastAPI, PostgreSQL, Docker Compose, Merchant, health, dashboard shell

### Sprint 2

- Customers, payments, failures, subscriptions, recovery cases
- Deterministic scoring/eligibility/suggested actions
- Synthetic data and recovery APIs

### Sprint 3

- Structured R.AI recommendations (`AIDecision`)
- Mock and optional live LLM providers
- Recommendation-only agent APIs and UI
- Immutable analysis history; comparison with baseline

### Sprint 4

- Deterministic Policy Engine (`apps/api/app/policies`)
- MerchantPolicy guardrails
- ActionExecutor (`apps/api/app/actions`) — the only path to provider calls
- ApprovalRequest workflow
- Append-only AuditLog
- MockPaymentProvider and RazorpayPaymentProvider (documented Payment Links / fetches)
- Execute, approvals, actions, audit, and policy APIs
- Recovery detail execution UI, Approval Center, real Audit page, Settings guardrails, dashboard execution KPIs

## Current technology stack

- Frontend: Next.js, TypeScript, App Router, Tailwind CSS
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, httpx
- Database: PostgreSQL 16
- Infrastructure: Docker, Docker Compose

## Important architectural decisions

- Layering: API routes stay thin; policy, execution, and provider logic stay out of routes.
- Frontend data access goes through `apps/web/src/lib/api-client.ts`.
- UUID primary keys and timezone-aware timestamps.
- Payment-provider integrations are behind `apps/api/app/payment_providers`.
- There is no `retry_payment()` provider method. One-time recovery uses Payment Links. Subscription recovery is provider-managed/deferred.
- Mock mode (`AI_MODE=mock`, `PAYMENT_PROVIDER=mock`) runs the full workflow without credentials.
- Live Razorpay keys must be test-mode (`rzp_test_`). Live keys are rejected.

## Important safety constraints

- The LLM cannot call the payment provider.
- Routes cannot call provider methods directly.
- Execute requests cannot override merchant policy via query or body.
- Secrets are never sent to the frontend or written to audit/logs.
- Unknown/unsupported operations are blocked.

## Current Docker / runtime setup

Expected local ports: frontend `3000`, backend `8000`, PostgreSQL `5432`.

Copy `.env.example` to `.env`. Do not commit filled `.env` files with secrets.

## What remains to be built (after Sprint 4)

- Outcome observation / webhook handling for Payment Link paid events
- Evaluation harness
- Production authentication, notifications product, billing, fraud detection, advanced analytics
- Richer subscription lifecycle if Razorpay documents additional recovery APIs

## Future sprint roadmap

Recommended next sprint only after an explicit request:

**Sprint 5 — Outcome observation and evaluation**

- Payment Link / subscription status observation
- Recovery outcome recording
- Evaluation of recommendation vs execution vs collection
