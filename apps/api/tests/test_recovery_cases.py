from sqlalchemy import func, select

from app.models.recovery_case import RecoveryCase
from app.recovery.service import RecoveryAnalysisService
from tests.helpers import make_session, seed_failed_payment


def test_analysis_creates_a_case() -> None:
    session = make_session()
    payment = seed_failed_payment(session)
    result = RecoveryAnalysisService(session).analyze_failed_payments(payment_id=payment.id)
    assert result["cases_created"] == 1
    case = session.scalar(select(RecoveryCase).where(RecoveryCase.payment_id == payment.id))
    assert case is not None
    assert case.status in {"open", "blocked"}
    assert case.recoverability_score is not None


def test_repeated_analysis_does_not_duplicate_open_cases() -> None:
    session = make_session()
    payment = seed_failed_payment(session, email="repeat@example.invalid")
    service = RecoveryAnalysisService(session)
    first = service.analyze_failed_payments(payment_id=payment.id)
    second = service.analyze_failed_payments(payment_id=payment.id)
    count = session.scalar(select(func.count()).select_from(RecoveryCase).where(RecoveryCase.payment_id == payment.id))
    assert first["cases_created"] == 1
    assert second["cases_created"] == 0
    assert second["cases_updated"] == 1
    assert count == 1
