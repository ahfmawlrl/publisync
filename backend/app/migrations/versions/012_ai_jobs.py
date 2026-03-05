"""012: ai_jobs table (Phase 2, F03/F15).

Creates async AI job tracking table with ENUMs and RLS policies.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute("CREATE TYPE aijobstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')")
    op.execute("CREATE TYPE aijobtype AS ENUM ('SUBTITLE', 'SHORTFORM')")

    # ── ai_jobs ─────────────────────────────────────────
    op.create_table(
        "ai_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_type", postgresql.ENUM(name="aijobtype", create_type=False), nullable=False),
        sa.Column("status", postgresql.ENUM(name="aijobstatus", create_type=False),
                  server_default="PENDING", nullable=False),
        sa.Column("progress", sa.Integer, server_default="0", nullable=False),
        sa.Column("input_params", JSONB, nullable=True),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("media_asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_ai_jobs_org_id", "ai_jobs", ["organization_id"])
    op.create_index("idx_ai_jobs_user_id", "ai_jobs", ["user_id"])
    op.create_index("idx_ai_jobs_status", "ai_jobs", ["status"])
    op.create_index("idx_ai_jobs_job_type", "ai_jobs", ["job_type"])
    op.create_index("idx_ai_jobs_created_at", "ai_jobs", ["created_at"])

    # ── RLS ──────────────────────────────────────────────
    op.execute("ALTER TABLE ai_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON ai_jobs "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON ai_jobs "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sa_bypass ON ai_jobs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON ai_jobs")
    op.drop_table("ai_jobs")
    op.execute("DROP TYPE IF EXISTS aijobtype")
    op.execute("DROP TYPE IF EXISTS aijobstatus")
