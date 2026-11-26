from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.data.generate import generate_synthetic_dataset
from app.db.base import Base
from app.demo.service import DemoError, DemoService

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
public_demo_lock = Lock()


@router.post("/recovery")
def run_recovery_demo(db: Session = Depends(get_db)) -> dict:
    try:
        if get_settings().app_env == "public_demo":
            return _run_isolated_demo()
        return DemoService(db).run()
    except DemoError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message}) from exc


def _run_isolated_demo() -> dict:
    if not public_demo_lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="A demo is already running. Try again in a moment.")
    try:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            Base.metadata.create_all(engine)
            with Session(engine, autoflush=False) as session:
                generate_synthetic_dataset(
                    session, seed=42, customer_count=20, payment_count=80, reset=False, analyze=True
                )
                return DemoService(session).run()
        finally:
            engine.dispose()
    finally:
        public_demo_lock.release()
