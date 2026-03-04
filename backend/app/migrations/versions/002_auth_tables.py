"""auth tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ENUM types ────────────────────────────────────────
    user_role = postgresql.ENUM(
        "SYSTEM_ADMIN", "AGENCY_MANAGER", "AGENCY_OPERATOR", "CLIENT_DIRECTOR",
        name="user_role", create_type=True,
    )
    user_status = postgresql.ENUM(
        "ACTIVE", "INACTIVE", "LOCKED", "WITHDRAWN",
        name="user_status", create_type=True,
    )
    org_status = postgresql.ENUM(
        "ACTIVE", "INACTIVE", "SUSPENDED",
        name="org_status", create_type=True,
    )
    org_plan = postgresql.ENUM(
        "FREE", "BASIC", "PRO", "ENTERPRISE",
        name="org_plan", create_type=True,
    )
    invitation_status = postgresql.ENUM(
        "PENDING", "ACCEPTED", "EXPIRED", "REVOKED",
        name="invitation_status", create_type=True,
    )
    user_role.create(op.get_bind(), checkfirst=True)
    user_status.create(op.get_bind(), checkfirst=True)
    org_status.create(op.get_bind(), checkfirst=True)
    org_plan.create(op.get_bind(), checkfirst=True)
    invitation_status.create(op.get_bind(), checkfirst=True)

    # ── agencies ──────────────────────────────────────────
    op.create_table(
        "agencies",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_agencies_is_active", "agencies", ["is_active"], postgresql_where=sa.text("is_active = TRUE"))

    # ── organizations ─────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("status", org_status, nullable=False, server_default="ACTIVE"),
        sa.Column("plan", org_plan, nullable=False, server_default="BASIC"),
        sa.Column("logo_url", sa.String(512)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_quota_bytes", sa.BigInteger(), nullable=False, server_default="53687091200"),
        sa.Column("agency_id", sa.UUID(), sa.ForeignKey("agencies.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"])
    op.create_index("idx_organizations_agency_id", "organizations", ["agency_id"])

    # ── roles ─────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("permissions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("description", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ── users ─────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="AGENCY_OPERATOR"),
        sa.Column("status", user_status, nullable=False, server_default="ACTIVE"),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id")),
        sa.Column("profile_image_url", sa.String(512)),
        sa.Column("preferences", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_status", "users", ["status"])
    op.create_index("idx_users_organization_id", "users", ["organization_id"])

    # ── user_organizations ────────────────────────────────
    op.create_table(
        "user_organizations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_org"),
    )
    op.create_index("idx_user_organizations_user_id", "user_organizations", ["user_id"])
    op.create_index("idx_user_organizations_organization_id", "user_organizations", ["organization_id"])

    # ── refresh_tokens ────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("device_info", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    # ── password_reset_tokens ─────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    # ── invitations ───────────────────────────────────────
    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("organization_id", sa.UUID(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("status", invitation_status, nullable=False, server_default="PENDING"),
        sa.Column("invited_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_invitations_email", "invitations", ["email"])
    op.create_index("idx_invitations_organization_id", "invitations", ["organization_id"])

    # ── Seed: roles ───────────────────────────────────────
    op.execute("""
        INSERT INTO roles (id, name, permissions, description) VALUES
        (uuid_generate_v4(), 'SYSTEM_ADMIN', '["*"]', '시스템 관리자 — 전체 시스템 관리'),
        (uuid_generate_v4(), 'AGENCY_MANAGER', '["content.create","content.edit","content.delete","content.publish","comment.manage","channel.manage","user.invite","user.manage","workflow.manage","report.view","dashboard.view"]', '수탁업체 관리자 — 담당 기관 관리'),
        (uuid_generate_v4(), 'AGENCY_OPERATOR', '["content.create","content.edit","content.request_review","comment.manage","dashboard.view"]', '수탁업체 실무자 — 콘텐츠 작성/댓글 관리'),
        (uuid_generate_v4(), 'CLIENT_DIRECTOR', '["content.approve","content.reject","dashboard.view","channel.view","audit.view"]', '위탁기관 담당자 — 승인/조회')
    """)

    # ── Seed: SA user (password: admin123!) ────────────────
    op.execute("""
        INSERT INTO users (id, email, password_hash, name, role, status) VALUES
        (uuid_generate_v4(), 'admin@publisync.kr',
         '$2b$12$LJ3m4ys3Lg2nkRqGvKC7/.OpHdaN/ZxGcGhU0VAoiyIK0d3SUIzIy',
         '시스템 관리자', 'SYSTEM_ADMIN', 'ACTIVE')
    """)


def downgrade() -> None:
    op.drop_table("invitations")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_organizations")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("organizations")
    op.drop_table("agencies")

    op.execute("DROP TYPE IF EXISTS invitation_status")
    op.execute("DROP TYPE IF EXISTS org_plan")
    op.execute("DROP TYPE IF EXISTS org_status")
    op.execute("DROP TYPE IF EXISTS user_status")
    op.execute("DROP TYPE IF EXISTS user_role")
