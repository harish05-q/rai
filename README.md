# R.AI

R.AI is a Revenue AI platform for merchant revenue intelligence and recovery. Sprint 4 adds policy-bounded execution (Payment Links and provider-managed subscription recovery) on top of Sprints 1–3.

The LLM never executes payment-provider operations. The Policy Engine is deterministic application code.

## Architecture Overview

```text
apps/web  -> Next.js dashboard (recovery, approvals, audit, settings)
apps/api  -> FastAPI: recovery, agent, policy, actions, providers
postgres  -> PostgreSQL persistence
docs      -> Architecture, policy, payment execution
scripts   -> Synthetic data generation and demo seed
```

The frontend consumes backend APIs only through `apps/web/src/lib/api-client.ts`.

## Synthetic data

All generated customers are fake (`@example.invalid`). Generation uses a fixed seed.

```bash
python scripts/generate_data.py --seed 42 --customers 1000 --payments 10000
python scripts/seed_demo.py
```

In Docker, after migrations:

```bash
docker compose exec api python -m app.data.seed
```

Demo seed enables tightly scoped autonomous execution so low-value Payment Link recovery can be demonstrated in mock mode.

## Running migrations

```bash
cd apps/api
alembic upgrade head
```

In Docker:

```bash
docker compose run --rm api alembic upgrade head
```

## API (Sprint 4 additions)

- `GET /api/v1/policies` / `PUT /api/v1/policies`
- `GET /api/v1/policies/evaluate/{case_id}`
- `POST /api/v1/recovery/cases/{case_id}/execute`
- `GET /api/v1/actions` / `GET /api/v1/actions/{id}` / `GET /api/v1/actions/summary`
- `GET /api/v1/approvals` / `POST .../approve` / `POST .../reject`
- `GET /api/v1/audit`

Existing health, payments, recovery, and agent endpoints remain.

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

Automated tests use `PAYMENT_PROVIDER=mock` and do not require Razorpay credentials.

## Configuration

Default `.env.example`:

- `AI_MODE=mock`
- `PAYMENT_PROVIDER=mock`

To attempt Razorpay Test Mode (optional):

```text
PAYMENT_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
```

Never put secrets in source control. Live keys are rejected.

## Docs

- Scoring: `docs/recovery-intelligence.md`
- Policy: `docs/policy-engine.md`
- Execution: `docs/payment-execution.md`
- Agent handoff: `docs/PROJECT_CONTEXT.md`
