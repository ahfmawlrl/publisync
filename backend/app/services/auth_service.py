"""Auth business logic — login, refresh, password reset, invite accept."""

import structlog
from datetime import datetime, timedelta, timezone

from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    InvalidCredentialsError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserStatus
from app.models.user import (
    PasswordResetToken,
    RefreshToken,
    User,
    UserOrganization,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    InviteAcceptRequest,
    InviteVerifyResponse,
    LoginResponse,
    PasswordResetBody,
    RefreshResponse,
    TokenResponse,
    UserResponse,
)

logger = structlog.get_logger()

MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 30
PASSWORD_RESET_TOKEN_HOURS = 24


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    # ── Login ────────────────────────────────────────────

    async def login(self, email: str, password: str, remember_me: bool = False) -> LoginResponse:
        user = await self._repo.get_by_email(email)
        if user is None:
            raise InvalidCredentialsError()

        # Check lock
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise AccountLockedError()

        # Verify password
        if not verify_password(password, user.password_hash):
            await self._repo.increment_failed_login(user)
            if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
                await self._repo.lock_account(
                    user,
                    datetime.now(timezone.utc) + timedelta(minutes=LOCK_DURATION_MINUTES),
                )
                logger.warning("account_locked", user_id=str(user.id), email=email)
                raise AccountLockedError()
            raise InvalidCredentialsError()

        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError("Account is not active")

        # Reset failed count & update last login
        if user.failed_login_count > 0:
            await self._repo.reset_failed_login(user)
        await self._repo.update_last_login(user)

        # Generate tokens
        access = create_access_token(user.id, user.role.value)
        raw_refresh, refresh_hash, refresh_exp = create_refresh_token(user.id, remember_me)

        await self._repo.create_refresh_token(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=refresh_exp,
            )
        )

        logger.info("user_logged_in", user_id=str(user.id))
        return LoginResponse(
            tokens=TokenResponse(access_token=access, refresh_token=raw_refresh),
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                role=user.role.value,
                status=user.status.value,
                profile_image_url=user.profile_image_url,
            ),
        )

    # ── Refresh ──────────────────────────────────────────

    async def refresh(self, raw_refresh_token: str) -> RefreshResponse:
        token_hash = hash_token(raw_refresh_token)
        stored = await self._repo.get_refresh_token_by_hash(token_hash)
        if stored is None:
            raise AuthenticationError("Invalid or expired refresh token")

        # Rotation: revoke old, issue new
        await self._repo.revoke_refresh_token(stored)

        user = await self._repo.get_by_id(stored.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise AuthenticationError("User not found or inactive")

        access = create_access_token(user.id, user.role.value)
        logger.info("token_refreshed", user_id=str(user.id))
        return RefreshResponse(access_token=access)

    # ── Logout ───────────────────────────────────────────

    async def logout(self, user_id: str, refresh_token: str | None = None) -> None:
        if refresh_token:
            token_hash = hash_token(refresh_token)
            stored = await self._repo.get_refresh_token_by_hash(token_hash)
            if stored:
                await self._repo.revoke_refresh_token(stored)
        logger.info("user_logged_out", user_id=user_id)

    # ── Password Reset Request ───────────────────────────

    async def request_password_reset(self, email: str) -> str | None:
        """Return the raw token if user exists (for email sending). None if not found (silent)."""
        user = await self._repo.get_by_email(email)
        if user is None:
            # Silent — don't reveal whether the email exists
            return None

        raw = generate_token()
        token_hash = hash_token(raw)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_HOURS)

        await self._repo.create_password_reset_token(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        logger.info("password_reset_requested", user_id=str(user.id))
        return raw

    # ── Password Reset ───────────────────────────────────

    async def reset_password(self, data: PasswordResetBody) -> None:
        token_hash = hash_token(data.token)
        stored = await self._repo.get_password_reset_token_by_hash(token_hash)
        if stored is None:
            raise ValidationError("Invalid or expired reset token")

        user = await self._repo.get_by_id(stored.user_id)
        if user is None:
            raise NotFoundError("User not found")

        await self._repo.update_password(user, hash_password(data.new_password))
        await self._repo.mark_reset_token_used(stored)
        # Revoke all refresh tokens for security
        await self._repo.revoke_all_user_tokens(user.id)
        logger.info("password_reset_completed", user_id=str(user.id))

    # ── Invite Verify ────────────────────────────────────

    async def verify_invite(self, token: str) -> InviteVerifyResponse:
        token_hash = hash_token(token)
        invitation = await self._repo.get_invitation_by_token_hash(token_hash)
        if invitation is None:
            raise NotFoundError("Invalid or expired invitation")

        org = await self._repo.get_organization_by_id(invitation.organization_id)
        if org is None:
            raise NotFoundError("Organization not found")

        return InviteVerifyResponse(
            email=invitation.email,
            role=invitation.role.value,
            organization_name=org.name,
            expires_at=invitation.expires_at.isoformat(),
        )

    # ── Invite Accept ────────────────────────────────────

    async def accept_invite(self, data: InviteAcceptRequest) -> LoginResponse:
        token_hash = hash_token(data.token)
        invitation = await self._repo.get_invitation_by_token_hash(token_hash)
        if invitation is None:
            raise NotFoundError("Invalid or expired invitation")

        # Check if email already registered
        existing = await self._repo.get_by_email(invitation.email)
        if existing:
            raise ConflictError("A user with this email already exists")

        # Create user
        user = User(
            email=invitation.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role=invitation.role,
            status=UserStatus.ACTIVE,
            organization_id=invitation.organization_id,
        )
        await self._repo.create_user(user)

        # Add user-org mapping
        await self._repo.add_user_to_org(
            UserOrganization(
                user_id=user.id,
                organization_id=invitation.organization_id,
                role=invitation.role,
                is_primary=True,
            )
        )

        # Mark invitation as accepted
        await self._repo.accept_invitation(invitation)

        # Generate tokens and return login response
        access = create_access_token(user.id, user.role.value)
        raw_refresh, refresh_hash, refresh_exp = create_refresh_token(user.id)

        await self._repo.create_refresh_token(
            RefreshToken(
                user_id=user.id,
                token_hash=refresh_hash,
                expires_at=refresh_exp,
            )
        )

        logger.info("invite_accepted", user_id=str(user.id), org_id=str(invitation.organization_id))
        return LoginResponse(
            tokens=TokenResponse(access_token=access, refresh_token=raw_refresh),
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                name=user.name,
                role=user.role.value,
                status=user.status.value,
                profile_image_url=user.profile_image_url,
            ),
        )
