"""007: comments + reply_templates tables (Phase 1-B).

Create comments and reply_templates tables with ENUMs and RLS policies.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute("CREATE TYPE commentsentiment AS ENUM ('POSITIVE', 'NEUTRAL', 'NEGATIVE', 'DANGEROUS')")
    op.execute(
        "CREATE TYPE commentstatus AS ENUM "
        "('UNPROCESSED', 'PUBLISHED', 'HIDDEN', 'PENDING_DELETE', 'DELETED')"
    )

    # ── comments ────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id"), nullable=True),
        sa.Column("channel_id", UUID(as_uuid=True), sa.ForeignKey("channels.id"), nullable=False),
        sa.Column("platform", postgresql.ENUM(name="platformtype", create_type=False), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("author_profile_url", sa.String(512), nullable=True),
        sa.Column("parent_comment_id", UUID(as_uuid=True), sa.ForeignKey("comments.id"), nullable=True),
        sa.Column("sentiment", postgresql.ENUM(name="commentsentiment", create_type=False), nullable=True),
        sa.Column("sentiment_confidence", sa.Float, nullable=True),
        sa.Column("dangerous_level", sa.String(20), nullable=True),
        sa.Column("keywords", sa.ARRAY(sa.String(100)), nullable=True),
        sa.Column("status", postgresql.ENUM(name="commentstatus", create_type=False),
                  nullable=False, server_default="UNPROCESSED"),
        sa.Column("reply_text", sa.Text, nullable=True),
        sa.Column("reply_draft", sa.Text, nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hidden_reason", sa.Text, nullable=True),
        sa.Column("delete_reason", sa.Text, nullable=True),
        sa.Column("processed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("platform_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("channel_id", "external_id", name="uq_comments_channel_external"),
    )

    op.create_index("idx_comments_org_id", "comments", ["organization_id"])
    op.create_index("idx_comments_content_id", "comments", ["content_id"])
    op.create_index("idx_comments_channel_id", "comments", ["channel_id"])
    op.create_index("idx_comments_sentiment", "comments", ["sentiment"])
    op.create_index("idx_comments_status", "comments", ["status"])
    op.create_index("idx_comments_created_at", "comments", ["created_at"])

    # ── reply_templates ─────────────────────────────────
    op.create_table(
        "reply_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("variables", sa.ARRAY(sa.String(100)), nullable=True),
        sa.Column("usage_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("idx_templates_org_id", "reply_templates", ["organization_id"])
    op.create_index("idx_templates_category", "reply_templates", ["category"])
    op.create_index("idx_templates_is_active", "reply_templates", ["is_active"])

    # ── RLS ──────────────────────────────────────────────
    for table in ("comments", "reply_templates"):
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
    for table in ("reply_templates", "comments"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)

    op.execute("DROP TYPE IF EXISTS commentstatus")
    op.execute("DROP TYPE IF EXISTS commentsentiment")
