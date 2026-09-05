from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.actions.executor import ActionError, ActionExecutor
from app.api.deps import get_db
from app.models.merchant import Merchant
from app.policies.constants import POLICY_VERSION
from app.policies.service import get_or_create_merchant_policy
from app.schemas.policy import ExecutionPreview, MerchantPolicyResponse, MerchantPolicyUpdate

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


def _executor(db: Session = Depends(get_db)) -> ActionExecutor:
    return ActionExecutor(db)


def _default_merchant(db: Session, merchant_id: UUID | None) -> Merchant:
    if merchant_id is not None:
        merchant = db.get(Merchant, merchant_id)
        if merchant is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "merchant_not_found", "message": "Merchant was not found"},
            )
        return merchant
    merchant = db.scalar(select(Merchant).order_by(Merchant.created_at.asc()))
    if merchant is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "merchant_not_found", "message": "No merchant is configured"},
        )
    return merchant


@router.get("", response_model=MerchantPolicyResponse)
def get_policies(merchant_id: UUID | None = None, db: Session = Depends(get_db)) -> MerchantPolicyResponse:
    merchant = _default_merchant(db, merchant_id)
    policy = get_or_create_merchant_policy(db, merchant.id)
    db.commit()
    db.refresh(policy)
    return MerchantPolicyResponse.model_validate(policy)


@router.put("", response_model=MerchantPolicyResponse)
def update_policies(
    body: MerchantPolicyUpdate,
    merchant_id: UUID | None = None,
    db: Session = Depends(get_db),
) -> MerchantPolicyResponse:
    merchant = _default_merchant(db, merchant_id)
    policy = get_or_create_merchant_policy(db, merchant.id)
    updates = body.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(policy, key, value)
    policy.policy_version = POLICY_VERSION
    db.commit()
    db.refresh(policy)
    return MerchantPolicyResponse.model_validate(policy)


@router.get("/evaluate/{case_id}", response_model=ExecutionPreview)
def evaluate_case_policy(case_id: UUID, executor: ActionExecutor = Depends(_executor)) -> ExecutionPreview:
    try:
        return ExecutionPreview.model_validate(executor.preview(case_id))
    except ActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc
