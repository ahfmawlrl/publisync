"""contents, content_versions, publish_results

Revision ID: 005
Revises: 004
Create Date: 2026-03-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────
    content_status = postgresql.ENUM(
        "DRAFT", "PENDING_REVIEW", "IN_REVIEW", "APPROVED", "REJECTED",
        "SCHEDULED", "PUBLISHING", "PUBLISHED", "PARTIALLY_PUBLISHED",
        "PUBLISH_FAILED", "CANCELLED", "ARCHIVED",
        name="contentstatus", create_type=False,
    )
    publish_result_status = postgresql.ENUM(
        "PENDING", "SUCCESS", "FAILED",
        name="publishresultstatus", create_type=False,
    )
    content_status.create(op.get_bind(), checkfirst=True)
    publish_result_status.create(op.get_bind(), checkfirst=True)

    # ── contents ──────────────────────────────────────────
    op.create_table(
        "contents",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("status", content_status, nullable=False, server_default="DRAFT"),
        sa.Column("platforms", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("channel_ids", postgresql.ARRAY(sa.UUID()), server_default="{}"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("author_id", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("platform_contents", postgresql.JSONB(), server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("media_urls", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_contents_org_id", "contents", ["organization_id"])
    op.create_index("idx_contents_status", "contents", ["status"])
    op.create_index("idx_contents_author_id", "contents", ["author_id"])
    op.create_index("idx_contents_scheduled_at", "contents", ["scheduled_at"])
    op.create_index("idx_contents_search_vector", "contents", ["search_vector"], postgresql_using="gin")

    # tsvector trigger for full-text search
    op.execute("""
        CREATE OR REPLACE FUNCTION contents_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('simple', coalesce(NEW.title, '') || ' ' || coalesce(NEW.body, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER contents_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, body ON contents
        FOR EACH ROW EXECUTE FUNCTION contents_search_vector_update();
    """)

    # ── content_versions ──────────────────────────────────
    op.create_table(
        "content_versions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("content_id", sa.UUID(), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("changed_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_content_versions_content_id", "content_versions", ["content_id"])
    op.create_index("idx_content_versions_org_id", "content_versions", ["organization_id"])

    # ── publish_results ───────────────────────────────────
    op.create_table(
        "publish_results",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("content_id", sa.UUID(), sa.ForeignKey("contents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel_id", sa.UUID(), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("status", publish_result_status, nullable=False, server_default="PENDING"),
        sa.Column("platform_post_id", sa.String(255)),
        sa.Column("platform_url", sa.String(2048)),
        sa.Column("error_message", sa.Text()),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_publish_results_content_id", "publish_results", ["content_id"])
    op.create_index("idx_publish_results_org_id", "publish_results", ["organization_id"])
    op.create_index("idx_publish_results_channel_id", "publish_results", ["channel_id"])
    op.create_index("idx_publish_results_status", "publish_results", ["status"])

    # ── RLS policies ──────────────────────────────────────
    for table in ("contents", "content_versions", "publish_results"):
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
    for table in ("publish_results", "content_versions", "contents"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.execute("DROP TRIGGER IF EXISTS contents_search_vector_trigger ON contents")
    op.execute("DROP FUNCTION IF EXISTS contents_search_vector_update()")
    op.drop_table("publish_results")
    op.drop_table("content_versions")
    op.drop_table("contents")
    op.execute("DROP TYPE IF EXISTS publishresultstatus")
    op.execute("DROP TYPE IF EXISTS contentstatus")
