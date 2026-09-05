# Payment execution

Sprint 4 execution uses only documented Razorpay-supported primitives. R.AI does **not** invent a `retry_payment` endpoint. Razorpay Payments APIs retrieve/capture existing payments; they are not a generic collection mechanism for failed charges.

## Supported provider operations

| Operation | Mock | Razorpay Test Mode |
| --- | --- | --- |
| Create standard Payment Link `POST /v1/payment_links` | yes | yes |
| Notify Payment Link `POST /v1/payment_links/:id/notify_by/:medium` | yes | yes |
| Fetch payment `GET /v1/payments/:id` | yes | yes |
| Fetch subscription `GET /v1/subscriptions/:id` | yes | yes |
| Provider-managed subscription recovery | recorded as deferred | fetch subscription if id present; **no charge** |
| Direct retry / arbitrary charge | **not implemented** | **not implemented** |

## Action mapping

| Recommendation | Subscription context | Workflow |
| --- | --- | --- |
| `smart_retry` | recoverable subscription | `subscription_provider_managed` — Razorpay's own retry/dunning owns later charges. R.AI records deferred recovery. |
| `smart_retry` | one-time | Payment Link recovery workflow. This is **not** a replay of the original payment id. |
| `payment_reminder` | any | Create Payment Link; notify by email when merchant policy allows |
| `alternate_payment_method` | any | Create Payment Link with checkout method hints (`upi`, `netbanking`) where supported |
| `wait` | any | No provider action |
| `human_review` | any | Approval case; no provider action until a later approved recommendation |
| `do_nothing` | any | No provider action |

Refunds, transfers, discounts, captures-as-collection, and `retry_payment` are blocked by policy.

## Idempotency

`ActionExecution.request_fingerprint` is `sha256(case_id|action|workflow|amount|currency|v1)`.

If a succeeded, pending-approval, executing, or approved row exists for that fingerprint, a later execute returns `duplicate` and does not create another live Payment Link.

Failed executions may be retried (new row, same logical fingerprint lookup only blocks active/successful work).

Payment Link `reference_id` is derived from the fingerprint (`rai_` + 32 hex chars) so Razorpay-side duplicates are also constrained.

## Approval flow

1. Policy returns `require_approval`
2. `ActionExecution` is `pending_approval`
3. `ApprovalRequest` is `pending`
4. Approve runs the provider workflow
5. Reject marks execution `cancelled`

No provider call happens before approval.

## Mock mode

`PAYMENT_PROVIDER=mock` (default) returns structured mock results with `mock: true` and `https://mock.razorpay.invalid/...` URLs. It is not a Razorpay operation.

`MOCK_PROVIDER_FORCE_ERROR=true` forces provider failures for demos/tests.

## Razorpay test-mode setup

Set:

```text
PAYMENT_PROVIDER=razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_BASE_URL=https://api.razorpay.com
```

Live keys (`rzp_live_`) are rejected. Credentials never leave the API process.

If credentials are missing, the factory falls back to mock.

## Limitations

- Creating a Payment Link is a **new collection request**, not a retry of `pay_...`.
- Subscription recovery is **deferred / provider-managed**. R.AI does not claim a charge occurred.
- Payment Link `paid` webhooks / outcome observation are not in Sprint 4.
- Customer emails in synthetic data use `.invalid` and may be unsuitable for live notification tests.
