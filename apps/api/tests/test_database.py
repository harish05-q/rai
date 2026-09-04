from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine
from app.models import Merchant


def test_database_connection_executes_query() -> None:
    with engine.connect() as connection:
        result = connection.execute(text("select 1")).scalar_one()

    assert result == 1


def test_merchant_model_can_persist() -> None:
    Base.metadata.create_all(bind=engine)

    from app.db.session import SessionLocal

    with SessionLocal() as session:
        merchant = Merchant(name="Acme Retail", email="ops@example.com")
        session.add(merchant)
        session.commit()
        session.refresh(merchant)

        assert merchant.id is not None
        assert merchant.created_at is not None
        assert merchant.updated_at is not None

    Base.metadata.drop_all(bind=engine)
