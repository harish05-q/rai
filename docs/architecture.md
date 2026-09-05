# R.AI Architecture

R.AI is an autonomous revenue recovery platform for merchants. Sprint 4 adds bounded execution behind a deterministic Policy Engine.

## Operating Model

```text
R.AI Orchestrator (recommendation only)
-> Deterministic Policy Engine
-> Approval gate (when required)
-> Action Executor
-> Payment Provider (mock | Razorpay Test Mode)
-> Audit
```

The Policy Engine is application code. The Action Executor is the only module allowed to call a payment provider. The LLM never authorizes or executes payment operations.

## Current Components

- `apps/web`: operations UI (dashboard, payments, recovery, approvals, agent, audit, settings)
- `apps/api`: FastAPI service
- `apps/api/app/recovery`: deterministic scoring and cases
- `apps/api/app/agents`: recommendation layer
- `apps/api/app/policies`: Policy Engine and merchant guardrails
- `apps/api/app/actions`: Action Executor and idempotency fingerprints
- `apps/api/app/payment_providers`: mock and Razorpay adapters
- `apps/api/app/audit`: append-only audit records

## Data Model (Sprint 4 additions)

- `MerchantPolicy`: per-merchant execution guardrails
- `ActionExecution`: one attempted/completed bounded action, with request fingerprint
- `ApprovalRequest`: human gate for `require_approval`
- `AuditLog`: append-only events (recommendation, policy, approval, provider)

Existing Sprint 1–3 models are unchanged in purpose.

## Execution states

`proposed`, `blocked`, `pending_approval`, `approved`, `executing`, `succeeded`, `failed`, `cancelled`, `duplicate`

Policy outcomes are a separate field: `allow`, `require_approval`, `block`.

## Provider boundary

Supported operations: create Payment Link, notify Payment Link, fetch payment, fetch subscription, record provider-managed subscription recovery.

Not supported: generic retry charge, refunds, transfers, discounts, settlements.

Details: `docs/payment-execution.md` and `docs/policy-engine.md`.
