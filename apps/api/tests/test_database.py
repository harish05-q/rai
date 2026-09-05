from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Merchant


def test_database_connection_executes_query() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as connection:
        result = connection.execute(text("select 1")).scalar_one()
    assert result == 1


def test_merchant_model_can_persist() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with factory() as session:
        merchant = Merchant(name="Acme Retail", email="ops@example.com")
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        assert merchant.id is not None
        assert merchant.created_at is not None
        assert merchant.updated_at is not None
