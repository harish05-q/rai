from enum import StrEnum


class PaymentStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    ABANDONED = "abandoned"


class PaymentMethod(StrEnum):
    CARD = "card"
    UPI = "upi"
    NETBANKING = "netbanking"
    WALLET = "wallet"


class FailureCategory(StrEnum):
    TEMPORARY_TIMEOUT = "temporary_timeout"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    AUTHENTICATION_FAILURE = "authentication_failure"
    DECLINED = "declined"
    ABANDONED_CHECKOUT = "abandoned_checkout"
    OTHER = "other"
    NON_RECOVERABLE = "non_recoverable"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class RecoveryPriority(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecoveryEligibility(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    REVIEW = "review"


class SuggestedAction(StrEnum):
    SMART_RETRY = "smart_retry"
    PAYMENT_REMINDER = "payment_reminder"
    ALTERNATE_PAYMENT_METHOD = "alternate_payment_method"
    WAIT = "wait"
    HUMAN_REVIEW = "human_review"
    DO_NOTHING = "do_nothing"


class RecoveryCaseStatus(StrEnum):
    OPEN = "open"
    RECOVERED = "recovered"
    RESOLVED = "resolved"
    BLOCKED = "blocked"
