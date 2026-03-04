"""009: audit_logs + ai_usage_logs tables (Phase 1-B).

Create audit and AI tracking tables with ENUMs and RLS policies.
audit_logs: INSERT-ONLY (UPDATE/DELETE blocked via trigger).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute(
        "CREATE TYPE auditaction AS ENUM "
        "('CREATE', 'READ', 'UPDATE', 'DELETE', 'PUBLISH', 'APPROVE', 'REJECT', "
        "'LOGIN', 'LOGOUT', 'INVITE', 'EXPORT', 'CONNECT', 'DISCONNECT')"
    )
    op.execute(
        "CREATE TYPE aitasktype AS ENUM "
        "('TITLE', 'DESCRIPTION', 'HASHTAG', 'META_DESC', 'ALT_TEXT', 'SENTIMENT', "
        "'COMMENT_REPLY', 'TONE_CONVERT', 'CONTENT_REVIEW', 'SUBTITLE', 'SHORTFORM', "
        "'THUMBNAIL', 'TRANSLATION', 'REPORT', 'PREDICTION')"
    )

    # ── audit_logs ──────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_role", postgresql.ENUM(name="user_role", create_type=False),
                  nullable=True),
        sa.Column("action", postgresql.ENUM(name="auditaction", create_type=False), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_audit_logs_org_id", "audit_logs", ["organization_id"])
    op.create_index("idx_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("idx_audit_logs_org_action_created", "audit_logs",
                    ["organization_id", "action", "created_at"])

    # INSERT-ONLY trigger: block UPDATE/DELETE
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_logs_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is INSERT-ONLY. UPDATE and DELETE are not allowed.';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
    """)

    # ── ai_usage_logs ───────────────────────────────────
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("task_type", postgresql.ENUM(name="aitasktype", create_type=False), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer, server_default="0", nullable=False),
        sa.Column("estimated_cost", sa.Numeric(10, 6), server_default="0", nullable=False),
        sa.Column("processing_time_ms", sa.Integer, nullable=True),
        sa.Column("input_summary", sa.String(500), nullable=True),
        sa.Column("output_summary", sa.String(500), nullable=True),
        sa.Column("is_fallback", sa.Boolean, server_default="false", nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_ai_usage_org_id", "ai_usage_logs", ["organization_id"])
    op.create_index("idx_ai_usage_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("idx_ai_usage_task_type", "ai_usage_logs", ["task_type"])
    op.create_index("idx_ai_usage_model", "ai_usage_logs", ["model"])
    op.create_index("idx_ai_usage_created_at", "ai_usage_logs", ["created_at"])
    op.create_index("idx_ai_usage_org_month", "ai_usage_logs", ["organization_id", "created_at"])

    # ── RLS ──────────────────────────────────────────────
    for table in ("audit_logs", "ai_usage_logs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (organization_id = current_setting('app.current_org_id')::uuid)"
        )
        op.execute(
            f"CREATE POLICY sa_bypass ON {table} "
            f"USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
        )


def downgrade() -> None:
    for table in ("ai_usage_logs", "audit_logs"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS audit_logs_immutable()")

    op.drop_table("ai_usage_logs")
    op.drop_table("audit_logs")

    op.execute("DROP TYPE IF EXISTS aitasktype")
    op.execute("DROP TYPE IF EXISTS auditaction")
