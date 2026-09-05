from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.recovery_outcome import RecoveryOutcome
from app.outcomes.service import OutcomeError, OutcomeService

router = APIRouter(prefix="/api/v1/outcomes", tags=["outcomes"])


@router.get("/cases/{case_id}")
def list_case_outcomes(
    case_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    items = db.scalars(
        select(RecoveryOutcome)
        .where(RecoveryOutcome.recovery_case_id == case_id)
        .order_by(RecoveryOutcome.observed_at.desc())
        .limit(limit)
    ).all()
    return {"items": [_serialize(item) for item in items], "total": len(items)}


@router.post("/cases/{case_id}/observe")
def observe_case_outcome(case_id: UUID, simulate: bool = False, db: Session = Depends(get_db)) -> dict:
    try:
        outcome = OutcomeService(db).observe_case(case_id, simulate=simulate)
        if outcome is None:
            raise HTTPException(status_code=404, detail={"code": "outcome_not_found", "message": "No outcome was observed"})
        return _serialize(outcome)
    except OutcomeError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


def _serialize(item: RecoveryOutcome) -> dict:
    return {
        "id": str(item.id),
        "recovery_case_id": str(item.recovery_case_id),
        "action_execution_id": str(item.action_execution_id) if item.action_execution_id else None,
        "provider": item.provider,
        "provider_reference": item.provider_reference,
        "workflow": item.workflow,
        "outcome_status": item.outcome_status,
        "amount_attempted": str(item.amount_attempted) if item.amount_attempted is not None else None,
        "amount_recovered": str(item.amount_recovered) if item.amount_recovered is not None else None,
        "currency": item.currency,
        "observed_at": item.observed_at.isoformat(),
        "source": item.source,
        "extra": item.extra,
    }