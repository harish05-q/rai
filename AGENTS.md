# R.AI Repository Constitution

This repository contains R.AI (Revenue AI), a Razorpay AI Buildathon project for an autonomous revenue recovery platform for merchants.

Future Codex tasks must follow this document before making product or architectural changes. When this file conflicts with an ad hoc implementation idea, this file wins unless the user explicitly changes the project direction.

## Product Direction

R.AI's long-term workflow is:

1. Payment event
2. Diagnosis
3. Recoverability assessment
4. Recovery strategy
5. Deterministic policy validation
6. Bounded execution
7. Outcome observation
8. Audit trail
9. Evaluation

The system is expected to integrate with Razorpay Test Mode eventually, but no real payment execution should be introduced until explicitly requested.

The LLM must never have unrestricted authority over payment operations.

## Current Sprint Scope

Sprint 1–4 are complete. Do not start Sprint 5 automatically.

Sprint 4 added a deterministic Policy Engine, human approval, a bounded Action
Executor, mock and Razorpay Test Mode providers (Payment Links and documented
fetches only), and append-only audit logs.

Do not implement these features unless a later task explicitly asks for them:

- Production authentication
- Notifications products (beyond Payment Link notify)
- Billing
- Fraud detection products
- Advanced analytics
- Refunds, transfers, discounts, or invented retry-charge APIs

The LLM must never have unrestricted authority over payment operations.

## Target Structure

Prefer this root structure:

```text
apps/web
apps/api
data
docs
scripts
```

Additional directories may be introduced when implementation requires them, especially:

```text
apps/api/app/agents
apps/api/app/tools
apps/api/app/policies
apps/api/app/payment_providers
apps/api/app/recovery
apps/api/app/analytics
apps/api/app/audit
```

Do not create placeholder modules merely to make the tree look complete.

## Technology Stack

Frontend:

- Next.js
- TypeScript
- App Router
- Tailwind CSS

Backend:

- Python 3.12+
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- Alembic

Database:

- PostgreSQL

Infrastructure:

- Docker
- Docker Compose

## Engineering Principles

- Prefer simple, production-quality architecture over premature abstraction.
- Keep business logic out of UI components.
- Keep API route handlers thin.
- Use strong typing wherever practical.
- Never hardcode secrets or API credentials.
- Never commit `.env` files containing secrets.
- Prefer deterministic code for financial controls and safety rules.
- Validate structured LLM output before it can influence business actions.
- Make every autonomous action auditable.
- Require human approval support for high-risk or high-value actions.
- Keep all payment-provider integrations behind an abstraction.
- Keep mock and test payment behavior available without external credentials.
- Write tests for meaningful business behavior, not superficial line coverage.
- Do not introduce dependencies without a reason.
- Do not silently change architectural decisions.
- Do not claim a feature works without verifying it.

## Frontend Principles

R.AI should feel like a premium fintech operations platform:

- Clean
- Professional
- Data-oriented
- Restrained
- Accessible
- Responsive

Avoid:

- Excessive gradients
- Gimmicky AI visuals
- Unnecessary animations
- Cluttered dashboards
- Giant monolithic components

Keep API and data access separate from presentation. Use reusable components where repetition exists, but avoid abstraction that does not remove real complexity.

## Backend Principles

Use a layered approach where useful:

```text
API/routes -> services/domain logic -> persistence/data access
```

Keep route handlers thin. Validate external input with Pydantic. Use typed database models. Keep financial calculations explicit, deterministic, and testable.

Do not over-engineer repositories or service classes when a small, direct implementation is clearer.

## AI And Agent Boundaries

Future agent architecture should follow this shape:

```text
R.AI Orchestrator
-> Diagnosis
-> Recovery Strategy
-> Policy Engine
-> Action Executor
-> Provider Tools
-> Audit
```

The Policy Engine must be deterministic application code.

The LLM may propose an action. The application decides whether that action is permitted.

Never trust raw model output as authorization. Never expose hidden chain-of-thought in the product.

Store concise decision summaries, relevant inputs, structured outputs, policy results, and outcomes.

## Payment Safety

Future autonomous actions may include:

- Smart retry
- Payment reminder
- Alternate payment-method suggestion

Potentially restricted actions include:

- Refunds
- Discounts
- High-value transactions
- Suspicious transactions

The system must support:

- Maximum retry limits
- High-value thresholds
- Approval requirements
- Stopping conditions
- Idempotency
- Audit logging

Never invent authorization behavior. When authorization or approval rules are unclear, keep the action blocked or mock-only until the user defines the policy.

## Testing And Verification

Every sprint must include appropriate automated tests.

At minimum, verify:

- Application startup
- API health
- Database connectivity
- Important domain behavior
- Error handling for changed functionality

When possible, run:

- Backend tests
- Frontend lint and type checks
- Relevant integration tests
- Browser verification for UI changes

Inspect and fix failures before reporting completion. If a check cannot be run, state why.

## Development Workflow

For every task:

1. Inspect the repository first.
2. Create a concise implementation plan.
3. Implement only the requested scope.
4. Run relevant checks.
5. Inspect and fix failures.
6. Inspect the final diff.
7. Summarize what changed, what was verified, remaining issues, and the recommended next step.

Keep commits logically scoped when commits are requested. Do not rewrite existing history unless explicitly instructed. Never commit secrets.

## Code Quality

Prefer readable code over clever code. Prefer explicit names over abbreviations.

Avoid:

- TODOs pretending to be implementations
- Dead code
- Unnecessary comments
- Giant files
- Giant functions
- Duplicated configuration
- Ignored errors

When uncertain about a design choice, choose the simplest option consistent with this architecture. Document material decisions that affect future work.
