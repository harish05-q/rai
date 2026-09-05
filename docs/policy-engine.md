# Policy Engine

The Policy Engine is deterministic application code in `apps/api/app/policies/engine.py`. The LLM never decides whether an action is authorized.

## Flow

```text
Latest R.AI recommendation
-> map action to provider workflow
-> evaluate MerchantPolicy + case context
-> ALLOW | REQUIRE_APPROVAL | BLOCK
-> Action Executor (only if ALLOW, or after human approval)
```

Routes do not call payment providers. Execute and approve both go through `ActionExecutor`.

## Inputs

- Recommended action
- Amount, attempts, prior recovery executions
- Subscription recoverability
- Eligibility, AI recoverability assessment, confidence, concerns
- MerchantPolicy snapshot

## Defaults (`apps/api/app/policies/constants.py`)

- `autonomous_execution`: false (demo seed enables tightly scoped true)
- `max_autonomous_action_amount`: ₹25,000
- `high_value_threshold`: ₹50,000
- `max_recovery_attempts`: 3
- Payment Link / notifications / subscription recovery: allowed
- High-value and uncertain cases: approval required
- Unknown or unsupported operations: blocked
- Policy version: `2026.04.1`

Demo seed (`apply_demo_guardrails`) turns autonomous execution on below the high-value threshold so low-value Payment Link recovery can be demonstrated without changing Settings.

## Rule order

1. Unsupported / unknown action → BLOCK
2. `human_review` → REQUIRE_APPROVAL
3. `wait` / `do_nothing` → ALLOW (no provider)
4. Payment Link workflow while links disabled → BLOCK
5. Subscription workflow while subscription recovery disabled → BLOCK
6. Attempt limit reached → BLOCK
7. Uncertain/suspicious context (if configured) → REQUIRE_APPROVAL
8. High-value threshold (if configured) → REQUIRE_APPROVAL
9. Amount above autonomous cap → REQUIRE_APPROVAL
10. Autonomous execution off for provider actions → REQUIRE_APPROVAL
11. Otherwise ALLOW

Query/body parameters on execute cannot change these rules.

## Audit

Each execute writes at least:

- recommendation recorded (actor `ai`)
- policy evaluation (actor `system`)
- approval transition when applicable (actor `merchant` / `system`)
- provider result (actor `system` or `razorpay`)

Audit rows are insert-only.
