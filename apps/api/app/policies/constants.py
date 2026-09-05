from decimal import Decimal

from app.models.enums import SuggestedAction

POLICY_VERSION = "2026.04.1"

DEFAULT_AUTONOMOUS_EXECUTION = False
DEFAULT_MAX_AUTONOMOUS_ACTION_AMOUNT = Decimal("25000.00")
DEFAULT_HIGH_VALUE_THRESHOLD = Decimal("50000.00")
DEFAULT_MAX_RECOVERY_ATTEMPTS = 3
DEFAULT_PAYMENT_LINK_CREATION_ALLOWED = True
DEFAULT_NOTIFICATIONS_ALLOWED = True
DEFAULT_SUBSCRIPTION_RECOVERY_ALLOWED = True
DEFAULT_REQUIRE_APPROVAL_HIGH_VALUE = True
DEFAULT_REQUIRE_APPROVAL_UNCERTAIN = True

APPROVAL_TTL_HOURS = 72
MIN_CONFIDENCE_AUTONOMOUS = 0.40

SUSPICIOUS_TOKENS = ("fraud", "stolen", "chargeback", "suspicious", "account_closed")

PROVIDER_ACTIONS = frozenset(
    {
        SuggestedAction.SMART_RETRY,
        SuggestedAction.PAYMENT_REMINDER,
        SuggestedAction.ALTERNATE_PAYMENT_METHOD,
    }
)

NOOP_ACTIONS = frozenset(
    {
        SuggestedAction.WAIT,
        SuggestedAction.DO_NOTHING,
    }
)

BLOCKED_OPERATIONS = frozenset(
    {
        "refund",
        "refunds",
        "transfer",
        "transfers",
        "discount",
        "capture",
        "charge",
        "retry_payment",
        "direct_charge",
        "settlement",
        "payout",
    }
)

SUPPORTED_ACTIONS = frozenset(SuggestedAction)
