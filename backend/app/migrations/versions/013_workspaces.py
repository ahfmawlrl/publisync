"""013: workspaces table.

Creates workspaces table with unique constraint, index, and RLS policies.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── workspaces ────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("is_default", sa.Boolean, server_default="false", nullable=False),
        sa.Column("settings", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )

    op.create_index("idx_workspaces_org_id", "workspaces", ["organization_id"])

    # ── RLS ──────────────────────────────────────────────
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspaces FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON workspaces "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON workspaces "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sa_bypass ON workspaces")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON workspaces")
    op.drop_table("workspaces")
