# R.AI

R.AI is a Revenue AI platform for merchant revenue intelligence and recovery. Sprint 5 adds outcome observation, evaluation, analytics, and a deterministic mock demo on top of policy-bounded execution.

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

## Recovery lifecycle

Each case follows `Diagnosed -> Recommended -> Policy Checked -> Executed -> Observed -> Recovered`. Execution success is not recovery: a case is marked recovered only after an observed paid outcome. Payment Link recovery is observed through the provider abstraction; subscription recovery remains provider-managed/deferred and is recorded as pending observation where no documented collection operation exists.

All provider calls remain behind the mock or Razorpay Test Mode adapters. The Action Executor is the only provider caller, policy decisions are deterministic, and idempotency fingerprints plus append-only audit records protect repeated requests and preserve the decision trail.

## API (Sprint 5 additions)

- `GET /api/v1/analytics/overview|recovery|evaluation|actions|outcomes`
- `POST /api/v1/demo/recovery` (mock-only, no real charges or notifications)
- `GET /api/v1/outcomes/cases/{id}` / `POST .../observe`

Evaluation compares baseline and R.AI recommendations on the same stored cases with a deterministic synthetic recoverability model. Baseline recovery rate, R.AI recovery rate, agreement, block/approval rates, and lift are synthetic evaluation metrics, not live financial performance. Observed paid outcomes are labeled separately as database outcomes.

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

## Demo flow

1. Start PostgreSQL and the API, run migrations, and seed the demo dataset.
2. Start the web app and open **Analytics**.
3. Select **Run Recovery Demo**.
4. Follow the case through diagnosis, recommendation, deterministic policy validation, mock Payment Link execution, simulated observation, and the paid outcome.

The demo uses fake data and the mock provider. It never creates a real charge or notification.

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
