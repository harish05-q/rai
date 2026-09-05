from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.demo.service import DemoError, DemoService

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/recovery")
def run_recovery_demo(db: Session = Depends(get_db)) -> dict:
    try:
        return DemoService(db).run()
    except DemoError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc