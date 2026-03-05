"""008: notifications + notification_settings tables (Phase 1-B).

Create notification tables with ENUMs and RLS policies.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute(
        "CREATE TYPE notificationtype AS ENUM "
        "('PUBLISH_COMPLETE', 'PUBLISH_FAILED', 'APPROVAL_REQUEST', 'APPROVAL_RESULT', "
        "'DANGEROUS_COMMENT', 'COMMENT_NEW', 'TOKEN_EXPIRING', 'SYSTEM')"
    )
    op.execute(
        "CREATE TYPE notificationchannel AS ENUM "
        "('IN_APP', 'EMAIL', 'WEB_PUSH', 'TELEGRAM')"
    )

    # ── notifications ───────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", postgresql.ENUM(name="notificationtype", create_type=False), nullable=False),
        sa.Column("channel", postgresql.ENUM(name="notificationchannel", create_type=False),
                  nullable=False, server_default="IN_APP"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("payload", JSONB, nullable=True),
        sa.Column("is_read", sa.Boolean, server_default="false", nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_notifications_org_id", "notifications", ["organization_id"])
    op.create_index("idx_notifications_user_id", "notifications", ["user_id"])
    op.create_index("idx_notifications_is_read", "notifications", ["is_read"])
    op.create_index("idx_notifications_type", "notifications", ["type"])
    op.create_index("idx_notifications_created_at", "notifications", ["created_at"])

    # ── notification_settings ───────────────────────────
    op.create_table(
        "notification_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channels", JSONB, nullable=False,
                  server_default='{"web":{"enabled":true},"email":{"enabled":true},"telegram":{"enabled":false},"webPush":{"enabled":false}}'),
        sa.Column("push_subscription", JSONB, nullable=True),
        sa.Column("telegram_chat_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_notification_settings_org_user"),
    )

    op.create_index("idx_notification_settings_user_id", "notification_settings", ["user_id"])

    # ── RLS ──────────────────────────────────────────────
    for table in ("notifications", "notification_settings"):
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
    for table in ("notification_settings", "notifications"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.drop_table(table)

    op.execute("DROP TYPE IF EXISTS notificationchannel")
    op.execute("DROP TYPE IF EXISTS notificationtype")
