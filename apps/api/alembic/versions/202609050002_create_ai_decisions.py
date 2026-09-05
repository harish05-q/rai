"""create ai_decisions

Revision ID: 202609050002
Revises: 202609050001
Create Date: 2026-09-05 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202609050002"
down_revision: Union[str, None] = "202609050001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("ai_mode", sa.String(length=16), nullable=False),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("diagnosis", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.String(length=1024), nullable=False),
        sa.Column("alternative_action", sa.String(length=64), nullable=True),
        sa.Column("timing", sa.String(length=32), nullable=False),
        sa.Column("concerns", sa.JSON(), nullable=False),
        sa.Column("baseline_action", sa.String(length=64), nullable=False),
        sa.Column("baseline_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("comparison_status", sa.String(length=16), nullable=False),
        sa.Column("comparison_reason", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recovery_case_id"], ["recovery_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_decisions_recovery_case_id", "ai_decisions", ["recovery_case_id"])
    op.create_index("ix_ai_decisions_created_at", "ai_decisions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_decisions_created_at", table_name="ai_decisions")
    op.drop_index("ix_ai_decisions_recovery_case_id", table_name="ai_decisions")
    op.drop_table("ai_decisions")
