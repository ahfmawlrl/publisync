"""approval_workflows, approval_requests, approval_histories

Revision ID: 006
Revises: 005
Create Date: 2026-03-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────
    approval_status = postgresql.ENUM(
        "PENDING_REVIEW", "IN_REVIEW", "APPROVED", "REJECTED",
        name="approvalstatus", create_type=True,
    )
    approval_action = postgresql.ENUM(
        "SUBMIT", "APPROVE", "REJECT", "REQUEST_CHANGES",
        name="approvalaction", create_type=True,
    )
    approval_status.create(op.get_bind(), checkfirst=True)
    approval_action.create(op.get_bind(), checkfirst=True)

    # ── approval_workflows ────────────────────────────────
    op.create_table(
        "approval_workflows",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("steps", postgresql.JSONB(), server_default="[]"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_approval_workflows_org_id", "approval_workflows", ["organization_id"])

    # ── approval_requests ─────────────────────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("content_id", sa.UUID(), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), sa.ForeignKey("approval_workflows.id")),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", approval_status, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("requested_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_approval_requests_org_id", "approval_requests", ["organization_id"])
    op.create_index("idx_approval_requests_content_id", "approval_requests", ["content_id"])
    op.create_index("idx_approval_requests_status", "approval_requests", ["status"])

    # ── approval_histories ────────────────────────────────
    op.create_table(
        "approval_histories",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("request_id", sa.UUID(), sa.ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("action", approval_action, nullable=False),
        sa.Column("reviewer_id", sa.UUID(), sa.ForeignKey("users.id")),
        sa.Column("comment", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_approval_histories_request_id", "approval_histories", ["request_id"])
    op.create_index("idx_approval_histories_org_id", "approval_histories", ["organization_id"])

    # ── RLS policies ──────────────────────────────────────
    for table in ("approval_workflows", "approval_requests", "approval_histories"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (organization_id = current_setting('app.current_org_id')::uuid)
        """)
        op.execute(f"""
            CREATE POLICY sa_bypass ON {table}
                USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')
        """)


def downgrade() -> None:
    for table in ("approval_histories", "approval_requests", "approval_workflows"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("approval_histories")
    op.drop_table("approval_requests")
    op.drop_table("approval_workflows")
    op.execute("DROP TYPE IF EXISTS approvalaction")
    op.execute("DROP TYPE IF EXISTS approvalstatus")
