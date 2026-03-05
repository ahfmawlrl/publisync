"""010: media_assets, media_folders, content_media_assets tables (Phase 2, F11).

Creates media library tables with ENUMs and RLS policies.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute("CREATE TYPE mediatype AS ENUM ('IMAGE', 'VIDEO', 'AUDIO', 'DOCUMENT')")

    # ── media_folders ───────────────────────────────────
    op.create_table(
        "media_folders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("media_folders.id", ondelete="CASCADE"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_media_folders_org_id", "media_folders", ["organization_id"])
    op.create_index("idx_media_folders_parent_id", "media_folders", ["parent_id"])
    op.create_unique_constraint("uq_media_folder_name", "media_folders",
                                ["organization_id", "parent_id", "name"])

    # ── media_assets ────────────────────────────────────
    op.create_table(
        "media_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("media_type", postgresql.ENUM(name="mediatype", create_type=False), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("width", sa.Integer, nullable=True),
        sa.Column("height", sa.Integer, nullable=True),
        sa.Column("tags", ARRAY(sa.String), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("folder_id", UUID(as_uuid=True),
                  sa.ForeignKey("media_folders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("version", sa.Integer, server_default="1", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("thumbnail_url", sa.String(1024), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_media_assets_org_id", "media_assets", ["organization_id"])
    op.create_index("idx_media_assets_folder_id", "media_assets", ["folder_id"])
    op.create_index("idx_media_assets_media_type", "media_assets", ["media_type"])
    op.create_index("idx_media_assets_created_by", "media_assets", ["created_by"])
    op.create_index("idx_media_assets_tags", "media_assets", ["tags"], postgresql_using="gin")
    op.create_index("idx_media_assets_created_at", "media_assets", ["created_at"])

    # ── content_media_assets ────────────────────────────
    op.create_table(
        "content_media_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", UUID(as_uuid=True),
                  sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_asset_id", UUID(as_uuid=True),
                  sa.ForeignKey("media_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_unique_constraint("uq_content_media", "content_media_assets",
                                ["content_id", "media_asset_id"])
    op.create_index("idx_content_media_content_id", "content_media_assets", ["content_id"])
    op.create_index("idx_content_media_asset_id", "content_media_assets", ["media_asset_id"])
    op.create_index("idx_content_media_org_id", "content_media_assets", ["organization_id"])

    # ── RLS ──────────────────────────────────────────────
    for table in ("media_folders", "media_assets", "content_media_assets"):
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
    for table in ("content_media_assets", "media_assets", "media_folders"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_table("content_media_assets")
    op.drop_table("media_assets")
    op.drop_table("media_folders")

    op.execute("DROP TYPE IF EXISTS mediatype")
