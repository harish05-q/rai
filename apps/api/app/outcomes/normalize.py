from hashlib import sha256

from app.models.enums import OutcomeStatus


PROVIDER_STATUS_MAP = {
    "created": OutcomeStatus.CREATED,
    "issued": OutcomeStatus.CREATED,
    "sent": OutcomeStatus.SENT,
    "notified": OutcomeStatus.SENT,
    "opened": OutcomeStatus.OPENED,
    "paid": OutcomeStatus.PAID,
    "captured": OutcomeStatus.PAID,
    "partially_paid": OutcomeStatus.PAID,
    "expired": OutcomeStatus.EXPIRED,
    "cancelled": OutcomeStatus.CANCELLED,
    "canceled": OutcomeStatus.CANCELLED,
    "failed": OutcomeStatus.FAILED,
    "deferred": OutcomeStatus.PENDING,
    "pending": OutcomeStatus.PENDING,
    "skipped": OutcomeStatus.PENDING,
    "unknown": OutcomeStatus.UNKNOWN,
}


def normalize_provider_status(raw: str | None) -> OutcomeStatus:
    if not raw:
        return OutcomeStatus.UNKNOWN
    key = raw.strip().lower()
    return PROVIDER_STATUS_MAP.get(key, OutcomeStatus.UNKNOWN)


def outcome_fingerprint(
    *,
    provider: str,
    provider_reference: str | None,
    outcome_status: str,
    action_execution_id: str | None = None,
) -> str:
    """Deterministic identity: provider + reference + status (execution id if no reference)."""

    reference = (provider_reference or "").strip()
    material = f"{provider.strip().lower()}|{reference}|{outcome_status.strip().lower()}"
    if not reference and action_execution_id:
        material = f"{material}|{action_execution_id}"
    return sha256(material.encode("utf-8")).hexdigest()


def amount_recovered_for_status(status: OutcomeStatus, amount_attempted) -> object:
    if status == OutcomeStatus.PAID:
        return amount_attempted
    return None
