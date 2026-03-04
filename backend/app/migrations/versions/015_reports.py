"""015: reports table (Phase 3, F19).

Creates report_period/report_status ENUMs, reports table with RLS.
Adds REPORT value to aijobtype ENUM.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute("CREATE TYPE reportperiod AS ENUM ('WEEKLY', 'MONTHLY', 'QUARTERLY')")
    op.execute("CREATE TYPE reportstatus AS ENUM ('GENERATING', 'DRAFT', 'FINALIZED')")

    # Add REPORT to existing aijobtype ENUM
    op.execute("ALTER TYPE aijobtype ADD VALUE IF NOT EXISTS 'REPORT'")

    # ── reports table ───────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("period", postgresql.ENUM(name="reportperiod", create_type=False), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", postgresql.ENUM(name="reportstatus", create_type=False),
                  server_default="GENERATING", nullable=False),
        sa.Column("content", JSONB, server_default="{}", nullable=False),
        sa.Column("pdf_url", sa.String(1024), nullable=True),
        sa.Column("generated_by", sa.String(100), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # ── Indexes ─────────────────────────────────────────
    op.create_index("idx_reports_organization_id", "reports", ["organization_id"])
    op.create_index("idx_reports_period", "reports", ["period"])
    op.create_index("idx_reports_status", "reports", ["status"])
    op.create_index("idx_reports_created_at", "reports", ["created_at"])

    # ── RLS ──────────────────────────────────────────────
    op.execute("ALTER TABLE reports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE reports FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON reports "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON reports "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sa_bypass ON reports")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON reports")
    op.drop_table("reports")
    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS reportperiod")
    # Note: cannot remove REPORT from aijobtype ENUM in downgrade
