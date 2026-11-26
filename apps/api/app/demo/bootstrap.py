"""Seed a new hosted demo once, preserving its data across restarts."""

from sqlalchemy import select

from app.data.generate import generate_synthetic_dataset
from app.db.session import SessionLocal
from app.models import Merchant


def seed_if_empty() -> None:
    with SessionLocal() as session:
        if session.scalar(select(Merchant.id).limit(1)) is None:
            generate_synthetic_dataset(
                session, seed=42, customer_count=40, payment_count=260, reset=False, analyze=True
            )
