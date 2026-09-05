from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.policies.service import get_or_create_merchant_policy
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


def _analyzed_case(email: str, amount: Decimal = Decimal("1299.00")) -> str:
    session = TestingSessionLocal()
    payment = seed_failed_payment(session, email=email, amount=amount)
    policy = get_or_create_merchant_policy(session, payment.merchant_id)
    policy.autonomous_execution = True
    policy.require_approval_for_uncertain = False
    session.commit()
    payment_id = str(payment.id)
    session.close()
    client = _client()
    analyzed = client.post("/api/v1/recovery/analyze", json={"payment_id": payment_id})
    assert analyzed.status_code == 200
    cases = client.get("/api/v1/recovery/cases").json()["items"]
    case_id = next(item["id"] for item in cases if item["payment_id"] == payment_id)
    rec = client.post(f"/api/v1/agent/analyze/{case_id}")
    assert rec.status_code == 200
    return case_id


def test_execute_recovery_and_actions_and_audit() -> None:
    case_id = _analyzed_case("api-exec@example.invalid")
    client = _client()
    policies = client.get("/api/v1/policies")
    assert policies.status_code == 200
    assert "autonomous_execution" in policies.json()

    executed = client.post(f"/api/v1/recovery/cases/{case_id}/execute")
    assert executed.status_code == 200
    body = executed.json()
    assert body["policy_decision"] == "allow"
    assert body["execution_status"] == "succeeded"
    assert body["provider"] == "mock"
    assert body["recommendation_only"] is False
    execution_id = body["execution_id"]

    fetched = client.get(f"/api/v1/actions/{execution_id}")
    assert fetched.status_code == 200
    listed = client.get("/api/v1/actions")
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    audit = client.get("/api/v1/audit", params={"case_id": case_id})
    assert audit.status_code == 200
    sources = {item["source"] for item in audit.json()["items"]}
    assert "recommendation" in sources
    assert "policy" in sources
    assert "provider" in sources


def test_approval_and_rejection() -> None:
    case_id = _analyzed_case("api-appr@example.invalid", Decimal("75000.00"))
    client = _client()
    pending = client.post(f"/api/v1/recovery/cases/{case_id}/execute")
    assert pending.status_code == 200
    assert pending.json()["execution_status"] == "pending_approval"
    approval_id = pending.json()["approval_id"]

    listed = client.get("/api/v1/approvals", params={"status": "pending"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    approved = client.post(f"/api/v1/approvals/{approval_id}/approve", json={"note": "ok"})
    assert approved.status_code == 200
    assert approved.json()["execution_status"] == "succeeded"

    reject_case = _analyzed_case("api-rej@example.invalid", Decimal("80000.00"))
    pending_reject = client.post(f"/api/v1/recovery/cases/{reject_case}/execute")
    reject_id = pending_reject.json()["approval_id"]
    rejected = client.post(f"/api/v1/approvals/{reject_id}/reject", json={"note": "no"})
    assert rejected.status_code == 200
    assert rejected.json()["execution_status"] == "cancelled"


def test_duplicate_execute_blocked() -> None:
    case_id = _analyzed_case("api-dup@example.invalid")
    client = _client()
    first = client.post(f"/api/v1/recovery/cases/{case_id}/execute")
    second = client.post(f"/api/v1/recovery/cases/{case_id}/execute")
    assert first.json()["execution_status"] == "succeeded"
    assert second.json()["execution_status"] == "duplicate"
