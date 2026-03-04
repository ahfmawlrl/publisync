import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, generate_uuid
from app.models.enums import InvitationStatus, OrgPlan, OrgStatus, UserRole, UserStatus


# ── agencies ──────────────────────────────────────────────
class Agency(Base, TimestampMixin):
    __tablename__ = "agencies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organizations: Mapped[list["Organization"]] = relationship(back_populates="agency")

    __table_args__ = (
        Index("idx_agencies_is_active", "is_active", postgresql_where=Text("is_active = TRUE")),
    )


# ── organizations ─────────────────────────────────────────
class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[OrgStatus] = mapped_column(Enum(OrgStatus, name="org_status"), nullable=False, default=OrgStatus.ACTIVE)
    plan: Mapped[OrgPlan] = mapped_column(Enum(OrgPlan, name="org_plan"), nullable=False, default=OrgPlan.BASIC)
    logo_url: Mapped[str | None] = mapped_column(String(512))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    storage_quota_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=53687091200)  # 50GB
    agency_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agencies.id"))

    agency: Mapped[Agency | None] = relationship(back_populates="organizations")
    user_organizations: Mapped[list["UserOrganization"]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
        Index("idx_organizations_agency_id", "agency_id"),
    )


# ── roles ─────────────────────────────────────────────────
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    permissions: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


# ── users ─────────────────────────────────────────────────
class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.AGENCY_OPERATOR)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ACTIVE)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    profile_image_url: Mapped[str | None] = mapped_column(String(512))
    preferences: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user_organizations: Mapped[list["UserOrganization"]] = relationship(back_populates="user")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
        Index("idx_users_status", "status"),
        Index("idx_users_organization_id", "organization_id"),
    )


# ── user_organizations ────────────────────────────────────
class UserOrganization(Base):
    __tablename__ = "user_organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", create_type=False), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    user: Mapped[User] = relationship(back_populates="user_organizations")
    organization: Mapped[Organization] = relationship(back_populates="user_organizations")

    __table_args__ = (
        Index("idx_user_organizations_user_id", "user_id"),
        Index("idx_user_organizations_organization_id", "organization_id"),
        {"info": {"unique_constraints": [("user_id", "organization_id")]}},
    )


# ── refresh_tokens ────────────────────────────────────────
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    device_info: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    user: Mapped[User] = relationship(back_populates="refresh_tokens")

    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_expires_at", "expires_at"),
    )


# ── password_reset_tokens ─────────────────────────────────
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        Index("idx_password_reset_tokens_user_id", "user_id"),
    )


# ── invitations ───────────────────────────────────────────
class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role", create_type=False), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[InvitationStatus] = mapped_column(Enum(InvitationStatus, name="invitation_status"), nullable=False, default=InvitationStatus.PENDING)
    invited_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    __table_args__ = (
        Index("idx_invitations_email", "email"),
        Index("idx_invitations_organization_id", "organization_id"),
    )


# ── system_announcements ─────────────────────────────────
class SystemAnnouncement(Base, TimestampMixin):
    __tablename__ = "system_announcements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="INFO")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
