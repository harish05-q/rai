"""create recovery outcomes and evaluation runs

Revision ID: 202609050004
Revises: 202609050003
Create Date: 2026-09-05 22:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202609050004"
down_revision: Union[str, None] = "202609050003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recovery_cases",
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="open"),
    )
    op.add_column(
        "recovery_cases",
        sa.Column("recovered_amount", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "recovery_cases",
        sa.Column("latest_outcome_status", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_recovery_cases_lifecycle_status", "recovery_cases", ["lifecycle_status"])
    op.create_table(
        "recovery_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("action_execution_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("workflow", sa.String(length=64), nullable=False),
        sa.Column("outcome_status", sa.String(length=32), nullable=False),
        sa.Column("amount_attempted", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("amount_recovered", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["recovery_case_id"], ["recovery_cases.id"]),
        sa.ForeignKeyConstraint(["action_execution_id"], ["action_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_recovery_outcomes_fingerprint"),
    )
    op.create_index("ix_recovery_outcomes_recovery_case_id", "recovery_outcomes", ["recovery_case_id"])
    op.create_index("ix_recovery_outcomes_action_execution_id", "recovery_outcomes", ["action_execution_id"])
    op.create_index("ix_recovery_outcomes_outcome_status", "recovery_outcomes", ["outcome_status"])
    op.create_index("ix_recovery_outcomes_observed_at", "recovery_outcomes", ["observed_at"])
    op.create_index(
        "ix_recovery_outcomes_provider_reference",
        "recovery_outcomes",
        ["provider", "provider_reference"],
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("data_source", sa.String(length=64), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("cases_evaluated", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("evaluation_runs")
    op.drop_index("ix_recovery_outcomes_provider_reference", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_observed_at", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_outcome_status", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_action_execution_id", table_name="recovery_outcomes")
    op.drop_index("ix_recovery_outcomes_recovery_case_id", table_name="recovery_outcomes")
    op.drop_table("recovery_outcomes")
    op.drop_index("ix_recovery_cases_lifecycle_status", table_name="recovery_cases")
    op.drop_column("recovery_cases", "latest_outcome_status")
    op.drop_column("recovery_cases", "recovered_amount")
    op.drop_column("recovery_cases", "lifecycle_status")
