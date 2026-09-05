from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.api.deps import get_db

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview")
def analytics_overview(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).overview()


@router.get("/recovery")
def analytics_recovery(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).recovery()


@router.get("/evaluation")
def analytics_evaluation(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).evaluation()


@router.get("/actions")
def analytics_actions(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).actions()


@router.get("/outcomes")
def analytics_outcomes(db: Session = Depends(get_db)) -> dict:
    return AnalyticsService(db).outcomes()