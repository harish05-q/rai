"""create execution guardrail tables

Revision ID: 202609050003
Revises: 202609050002
Create Date: 2026-09-05 21:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202609050003"
down_revision: Union[str, None] = "202609050002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "merchant_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("merchant_id", sa.Uuid(), nullable=False),
        sa.Column("autonomous_execution", sa.Boolean(), nullable=False),
        sa.Column("max_autonomous_action_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("high_value_threshold", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("max_recovery_attempts", sa.Integer(), nullable=False),
        sa.Column("payment_link_creation_allowed", sa.Boolean(), nullable=False),
        sa.Column("notifications_allowed", sa.Boolean(), nullable=False),
        sa.Column("subscription_recovery_allowed", sa.Boolean(), nullable=False),
        sa.Column("require_approval_for_high_value", sa.Boolean(), nullable=False),
        sa.Column("require_approval_for_uncertain", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merchant_id", name="uq_merchant_policies_merchant_id"),
    )
    op.create_table(
        "action_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("ai_decision_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("workflow", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("policy_decision", sa.String(length=32), nullable=False),
        sa.Column("approval_id", sa.Uuid(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["recovery_case_id"], ["recovery_cases.id"]),
        sa.ForeignKeyConstraint(["ai_decision_id"], ["ai_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_executions_recovery_case_id", "action_executions", ["recovery_case_id"])
    op.create_index("ix_action_executions_status", "action_executions", ["status"])
    op.create_index("ix_action_executions_created_at", "action_executions", ["created_at"])
    op.create_index("ix_action_executions_fingerprint", "action_executions", ["request_fingerprint"])
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=False),
        sa.Column("action_execution_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("requested_action", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(length=128), nullable=True),
        sa.Column("resolution_note", sa.String(length=1024), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["recovery_case_id"], ["recovery_cases.id"]),
        sa.ForeignKeyConstraint(["action_execution_id"], ["action_executions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_recovery_case_id", "approval_requests", ["recovery_case_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_requested_at", "approval_requests", ["requested_at"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("recovery_case_id", sa.Uuid(), nullable=True),
        sa.Column("ai_decision_id", sa.Uuid(), nullable=True),
        sa.Column("action_execution_id", sa.Uuid(), nullable=True),
        sa.Column("approval_id", sa.Uuid(), nullable=True),
        sa.Column("policy_decision", sa.String(length=32), nullable=True),
        sa.Column("requested_action", sa.String(length=64), nullable=True),
        sa.Column("executed_action", sa.String(length=64), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=1024), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recovery_case_id"], ["recovery_cases.id"]),
        sa.ForeignKeyConstraint(["ai_decision_id"], ["ai_decisions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_recovery_case_id", "audit_logs", ["recovery_case_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action_execution_id", "audit_logs", ["action_execution_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_execution_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_recovery_case_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_approval_requests_requested_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_recovery_case_id", table_name="approval_requests")
    op.drop_table("approval_requests")
    op.drop_index("ix_action_executions_fingerprint", table_name="action_executions")
    op.drop_index("ix_action_executions_created_at", table_name="action_executions")
    op.drop_index("ix_action_executions_status", table_name="action_executions")
    op.drop_index("ix_action_executions_recovery_case_id", table_name="action_executions")
    op.drop_table("action_executions")
    op.drop_table("merchant_policies")
