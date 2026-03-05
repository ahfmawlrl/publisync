"""011: calendar_events table (Phase 2, F10).

Creates calendar events table with ENUM and RLS policies.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ENUM types ──────────────────────────────────────
    op.execute(
        "CREATE TYPE calendareventtype AS ENUM "
        "('SCHEDULED_POST', 'HOLIDAY', 'ANNIVERSARY', 'CUSTOM')"
    )

    # ── calendar_events ─────────────────────────────────
    op.create_table(
        "calendar_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("content_id", UUID(as_uuid=True),
                  sa.ForeignKey("contents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", postgresql.ENUM(name="calendareventtype", create_type=False), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), server_default="ACTIVE", nullable=False),
        sa.Column("is_holiday", sa.Boolean, server_default="false", nullable=False),
        sa.Column("is_recurring", sa.Boolean, server_default="false", nullable=False),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index("idx_calendar_events_org_id", "calendar_events", ["organization_id"])
    op.create_index("idx_calendar_events_content_id", "calendar_events", ["content_id"])
    op.create_index("idx_calendar_events_event_date", "calendar_events", ["event_date"])
    op.create_index("idx_calendar_events_event_type", "calendar_events", ["event_type"])
    op.create_index("idx_calendar_events_org_date", "calendar_events",
                    ["organization_id", "event_date"])

    # ── RLS ──────────────────────────────────────────────
    op.execute("ALTER TABLE calendar_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE calendar_events FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON calendar_events "
        "USING (organization_id = current_setting('app.current_org_id')::uuid)"
    )
    op.execute(
        "CREATE POLICY sa_bypass ON calendar_events "
        "USING (current_setting('app.user_role', true) = 'SYSTEM_ADMIN')"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS sa_bypass ON calendar_events")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON calendar_events")
    op.drop_table("calendar_events")
    op.execute("DROP TYPE IF EXISTS calendareventtype")
