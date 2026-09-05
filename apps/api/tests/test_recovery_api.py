from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from tests.helpers import seed_failed_payment

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def _client() -> TestClient:
    def override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_payments_and_recovery_api() -> None:
    session = TestingSessionLocal()
    payment = seed_failed_payment(session, email="api@example.invalid")
    session.close()
    client = _client()

    payments = client.get("/api/v1/payments", params={"status": "failed"})
    assert payments.status_code == 200
    body = payments.json()
    assert body["total"] >= 1
    assert body["items"][0]["status"] == "failed"
    assert body["items"][0]["failure_category"] == "temporary_timeout"

    filtered = client.get("/api/v1/payments", params={"failure_category": "temporary_timeout"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1

    analyze = client.post("/api/v1/recovery/analyze", json={"payment_id": str(payment.id)})
    assert analyze.status_code == 200
    payload = analyze.json()
    assert payload["cases_created"] == 1
    assert payload["executed_payment_operations"] is False

    again = client.post("/api/v1/recovery/analyze", json={"payment_id": str(payment.id)})
    assert again.json()["cases_created"] == 0
    assert again.json()["cases_updated"] == 1

    cases = client.get("/api/v1/recovery/cases")
    assert cases.status_code == 200
    assert cases.json()["total"] == 1
    item = cases.json()["items"][0]
    assert item["suggested_action"] == "smart_retry"
    assert 0 <= float(item["recoverability_score"]) <= 1

    summary = client.get("/api/v1/recovery/summary")
    assert summary.status_code == 200
    metrics = summary.json()
    assert metrics["total_payments"] >= 1
    assert metrics["total_failed_payments"] >= 1
    assert metrics["open_recovery_cases"] >= 1
    assert "revenue_at_risk" in metrics
