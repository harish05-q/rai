import hashlib
from decimal import Decimal
from uuid import UUID


def execution_fingerprint(
    *,
    case_id: UUID,
    action: str,
    workflow: str,
    amount: Decimal,
    currency: str,
) -> str:
    payload = f"{case_id}|{action}|{workflow}|{amount:.2f}|{currency}|v1"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def payment_link_reference_id(fingerprint: str) -> str:
    return f"rai_{fingerprint[:32]}"
