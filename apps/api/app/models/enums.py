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


class FailureSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecoverabilityAssessment(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"
    UNCERTAIN = "uncertain"


class StrategyTiming(StrEnum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    NEXT_BILLING = "next_billing"
    AFTER_CUSTOMER_ACTION = "after_customer_action"
    NONE = "none"


class ComparisonStatus(StrEnum):
    ALIGNED = "aligned"
    DIFFERS = "differs"


class PolicyOutcome(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class ExecutionStatus(StrEnum):
    PROPOSED = "proposed"
    BLOCKED = "blocked"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DUPLICATE = "duplicate"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AuditActor(StrEnum):
    AI = "ai"
    MERCHANT = "merchant"
    SYSTEM = "system"
    RAZORPAY = "razorpay"


class RecoveryWorkflow(StrEnum):
    NONE = "none"
    PAYMENT_LINK = "payment_link"
    SUBSCRIPTION_PROVIDER_MANAGED = "subscription_provider_managed"
    APPROVAL_CASE = "approval_case"
