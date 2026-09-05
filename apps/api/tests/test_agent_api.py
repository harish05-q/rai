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


def test_agent_analyze_retrieve_and_activity() -> None:
    session = TestingSessionLocal()
    payment = seed_failed_payment(session, email="agent-api@example.invalid")
    session.close()
    client = _client()

    analyzed = client.post("/api/v1/recovery/analyze", json={"payment_id": str(payment.id)})
    assert analyzed.status_code == 200
    case_id = client.get("/api/v1/recovery/cases").json()["items"][0]["id"]

    missing = client.get("/api/v1/agent/cases/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404

    empty = client.get(f"/api/v1/agent/cases/{case_id}")
    assert empty.status_code == 200
    assert empty.json()["analysis"] is None

    result = client.post(f"/api/v1/agent/analyze/{case_id}")
    assert result.status_code == 200
    body = result.json()
    assert body["recommendation_only"] is True
    assert body["strategy"]["recommended_action"] in {
        "smart_retry",
        "payment_reminder",
        "alternate_payment_method",
        "wait",
        "human_review",
        "do_nothing",
    }
    assert 0 <= body["ai_confidence"] <= 1
    assert body["baseline_action"]
    assert body["provider"] == "mock"

    fetched = client.get(f"/api/v1/agent/cases/{case_id}")
    assert fetched.status_code == 200
    assert fetched.json()["analysis"]["id"] == body["id"]
    assert fetched.json()["history_count"] == 1

    again = client.post(f"/api/v1/agent/analyze/{case_id}")
    assert again.status_code == 200
    assert again.json()["id"] != body["id"]
    assert client.get(f"/api/v1/agent/cases/{case_id}").json()["history_count"] == 2

    activity = client.get("/api/v1/agent/activity")
    assert activity.status_code == 200
    payload = activity.json()
    assert payload["total"] >= 2
    assert payload["items"][0]["title"].startswith("R.AI analyzed")

    summary = client.get("/api/v1/agent/summary")
    assert summary.status_code == 200
    metrics = summary.json()
    assert metrics["cases_analyzed"] >= 1
    assert metrics["recommendation_only"] is True

    status = client.get("/api/v1/agent/status")
    assert status.status_code == 200
    assert status.json()["ai_mode"] == "mock"

    batch = client.post("/api/v1/agent/analyze", json={"limit": 5, "skip_existing": True})
    assert batch.status_code == 200
    assert batch.json()["executed_payment_operations"] is False
    assert batch.json()["reused"] >= 1

    detail = client.get(f"/api/v1/recovery/cases/{case_id}")
    assert detail.status_code == 200
    assert detail.json()["external_payment_id"] == "pay_test"
