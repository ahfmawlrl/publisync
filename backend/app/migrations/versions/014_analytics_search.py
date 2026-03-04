"""014: analytics_snapshots and search_index_configs tables.

Creates analytics snapshot storage and search index configuration tables with RLS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── analytics_snapshots ───────────────────────────────
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel_id", UUID(as_uuid=True),
                  sa.ForeignKey("channels.id", ondelete="SET NULL"), nullable=True),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("metrics", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_analytics_snapshots_org_date", "analytics_snapshots",
                    ["organization_id", "snapshot_date"])

    # ── RLS for analytics_snapshots ───────────────────────
    op.execute("ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analytics_snapshots FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON analytics_snapshots "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON analytics_snapshots "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )

    # ── search_index_configs ──────────────────────────────
    op.create_table(
        "search_index_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("index_name", sa.String(100), nullable=False),
        sa.Column("settings", JSONB, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_search_index_configs_org_entity", "search_index_configs",
                    ["organization_id", "entity_type"])

    # ── RLS for search_index_configs ──────────────────────
    op.execute("ALTER TABLE search_index_configs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE search_index_configs FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON search_index_configs "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON search_index_configs "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )


def downgrade() -> None:
    # ── search_index_configs ──────────────────────────────
    op.execute("DROP POLICY IF EXISTS sa_bypass ON search_index_configs")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON search_index_configs")
    op.drop_table("search_index_configs")

    # ── analytics_snapshots ───────────────────────────────
    op.execute("DROP POLICY IF EXISTS sa_bypass ON analytics_snapshots")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON analytics_snapshots")
    op.drop_table("analytics_snapshots")
