"""channels and channel_histories

Revision ID: 004
Revises: 003
Create Date: 2026-03-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────
    platform_type = postgresql.ENUM(
        "YOUTUBE", "INSTAGRAM", "FACEBOOK", "X", "NAVER_BLOG",
        name="platformtype", create_type=True,
    )
    channel_status = postgresql.ENUM(
        "DISCONNECTED", "ACTIVE", "EXPIRING", "EXPIRED",
        name="channelstatus", create_type=True,
    )
    channel_event_type = postgresql.ENUM(
        "CONNECTED", "DISCONNECTED", "TOKEN_REFRESHED", "TOKEN_EXPIRED", "STATUS_CHANGED",
        name="channeleventtype", create_type=True,
    )
    platform_type.create(op.get_bind(), checkfirst=True)
    channel_status.create(op.get_bind(), checkfirst=True)
    channel_event_type.create(op.get_bind(), checkfirst=True)

    # ── channels ──────────────────────────────────────────
    op.create_table(
        "channels",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("platform", platform_type, nullable=False),
        sa.Column("platform_account_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", channel_status, nullable=False, server_default="DISCONNECTED"),
        sa.Column("access_token_enc", sa.Text()),
        sa.Column("refresh_token_enc", sa.Text()),
        sa.Column("token_expires_at", sa.DateTime(timezone=True)),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "platform", "platform_account_id", name="uq_channel_org_platform_account"),
    )
    op.create_index("idx_channels_org_id", "channels", ["organization_id"])
    op.create_index("idx_channels_status", "channels", ["status"])

    # ── channel_histories ─────────────────────────────────
    op.create_table(
        "channel_histories",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("channel_id", sa.UUID(), sa.ForeignKey("channels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", channel_event_type, nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("actor_id", sa.UUID(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_channel_histories_channel_id", "channel_histories", ["channel_id"])
    op.create_index("idx_channel_histories_org_id", "channel_histories", ["organization_id"])

    # ── RLS policies ──────────────────────────────────────
    for table in ("channels", "channel_histories"):
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
    for table in ("channel_histories", "channels"):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
    op.drop_table("channel_histories")
    op.drop_table("channels")
    op.execute("DROP TYPE IF EXISTS channeleventtype")
    op.execute("DROP TYPE IF EXISTS channelstatus")
    op.execute("DROP TYPE IF EXISTS platformtype")
