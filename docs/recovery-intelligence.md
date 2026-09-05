# Deterministic recovery intelligence

Sprint 2 scoring and strategy are **not** AI recommendations. They are the
baseline that later sprints will compare against R.AI's AI strategy.

No payment operation is executed by analysis, scoring, or suggested actions.

## Recoverability score

`apps/api/app/recovery/scoring.py` produces a value in `[0.0, 1.0]`.

```text
score = base(failure_category)
      + success_history_weight * success_ratio
      - failure_history_weight * min(failed_payments / 8, 1)
      + first_attempt_bonus  OR  - attempt_penalty * extra_attempts_ratio
      + active_subscription_bonus
      + high_value_bonus
      + reliable_customer_bonus
      - poor_customer_penalty
```

Weights, retry limits, and rupee thresholds live in
`apps/api/app/recovery/constants.py`.

The API returns operator-facing explanation factors such as:

- temporary bank failure
- 8 previous successful payments
- first failed attempt
- active subscription

## Eligibility

Eligible: failed or abandoned payment, potentially recoverable category, retry
limit not exceeded, no recovered/resolved case, required fields present.

Ineligible: already recovered, resolved, retry limit exceeded, non-recoverable
code/category, or already succeeded.

Review: missing customer/amount, or amount at or above the review threshold.

## Suggested action

Allowed values: `smart_retry`, `payment_reminder`, `alternate_payment_method`,
`wait`, `human_review`, `do_nothing`.

Default mapping is by failure category (timeout → retry, expired card →
alternate method, NSF → wait, abandoned → reminder). High-value review and
retry exhaustion override that mapping.
