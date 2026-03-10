"""Repository for User and related auth tables."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.user import (
    Invitation,
    Organization,
    PasswordResetToken,
    RefreshToken,
    User,
    UserOrganization,
)


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── User ─────────────────────────────────────────────

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self._db.add(user)
        await self._db.flush()
        return user

    async def increment_failed_login(self, user: User) -> int:
        """Atomically increment failed_login_count and return the new value."""
        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(failed_login_count=User.failed_login_count + 1)
            .returning(User.failed_login_count)
        )
        result = await self._db.execute(stmt)
        new_count = result.scalar_one()
        # Sync ORM instance to avoid stale read
        user.failed_login_count = new_count
        return new_count

    async def reset_failed_login(self, user: User) -> None:
        user.failed_login_count = 0
        user.locked_until = None
        await self._db.flush()

    async def lock_account(self, user: User, until: datetime) -> None:
        user.locked_until = until
        user.failed_login_count = 0
        await self._db.flush()

    async def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._db.flush()

    async def record_successful_login(self, user: User) -> None:
        """Reset failed login count and update last_login_at in a single flush."""
        if user.failed_login_count > 0:
            user.failed_login_count = 0
            user.locked_until = None
        user.last_login_at = datetime.now(UTC)
        await self._db.flush()

    async def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._db.flush()

    # ── UserOrganization ────────────────────────────────

    async def is_org_member(self, user_id: UUID, org_id: UUID) -> bool:
        stmt = select(UserOrganization).where(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == org_id,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_user_organizations(self, user_id: UUID) -> list[Organization]:
        stmt = (
            select(Organization)
            .join(UserOrganization, UserOrganization.organization_id == Organization.id)
            .where(UserOrganization.user_id == user_id)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def add_user_to_org(self, user_org: UserOrganization) -> None:
        self._db.add(user_org)
        await self._db.flush()

    # ── RefreshToken ────────────────────────────────────

    async def create_refresh_token(self, token: RefreshToken) -> None:
        self._db.add(token)
        await self._db.flush()

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(UTC),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        token.is_revoked = True
        await self._db.flush()

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        await self._db.execute(stmt)

    async def cleanup_expired_tokens(self, user_id: UUID) -> None:
        """Delete revoked or expired refresh tokens for a user to prevent table bloat."""
        from sqlalchemy import delete

        stmt = delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            (RefreshToken.is_revoked.is_(True)) | (RefreshToken.expires_at <= datetime.now(UTC)),
        )
        await self._db.execute(stmt)

    # ── PasswordResetToken ──────────────────────────────

    async def create_password_reset_token(self, token: PasswordResetToken) -> None:
        self._db.add(token)
        await self._db.flush()

    async def get_password_reset_token_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.is_used.is_(False),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_reset_token_used(self, token: PasswordResetToken) -> None:
        token.is_used = True
        await self._db.flush()

    async def invalidate_previous_reset_tokens(self, user_id: UUID) -> None:
        """Mark all unused reset tokens for a user as used before issuing a new one."""
        stmt = (
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.is_used.is_(False),
            )
            .values(is_used=True)
        )
        await self._db.execute(stmt)

    # ── Invitation ──────────────────────────────────────

    async def get_invitation_by_token_hash(self, token_hash: str) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.status == "PENDING",
            Invitation.expires_at > datetime.now(UTC),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_organization_by_id(self, org_id: UUID) -> Organization | None:
        return await self._db.get(Organization, org_id)

    async def create_invitation(self, invitation: Invitation) -> None:
        self._db.add(invitation)
        await self._db.flush()

    async def accept_invitation(self, invitation: Invitation) -> None:
        invitation.status = "ACCEPTED"
        invitation.accepted_at = datetime.now(UTC)
        await self._db.flush()

    # ── User listing / update / delete ───────────────────

    async def list_users(
        self,
        org_id: UUID | None = None,
        role: UserRole | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        base = select(User).where(User.deleted_at.is_(None))
        count_base = select(func.count()).select_from(User).where(User.deleted_at.is_(None))

        if org_id:
            base = base.join(UserOrganization).where(UserOrganization.organization_id == org_id)
            count_base = count_base.join(UserOrganization).where(
                UserOrganization.organization_id == org_id
            )
        if role:
            base = base.where(User.role == role)
            count_base = count_base.where(User.role == role)

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_user(self, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        await self._db.flush()
        return user

    async def soft_delete_user(self, user: User) -> None:
        user.deleted_at = datetime.now(UTC)
        await self._db.flush()

    async def get_user_org_mappings(self, user_id: UUID) -> list[UserOrganization]:
        stmt = select(UserOrganization).where(UserOrganization.user_id == user_id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
