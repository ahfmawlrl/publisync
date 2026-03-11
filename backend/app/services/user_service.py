"""User CRUD business logic."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import generate_token, hash_token
from app.models.enums import UserRole, UserStatus
from app.models.user import Invitation, User, UserOrganization
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreateRequest, UserUpdateRequest

logger = structlog.get_logger()

INVITE_TOKEN_EXPIRE_DAYS = 7


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def list_users(
        self,
        org_id: UUID | None = None,
        role: UserRole | None = None,
        search: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        offset = (page - 1) * limit
        return await self._repo.list_users(
            org_id=org_id, role=role, search=search, status=status, offset=offset, limit=limit,
        )

    async def get_user(self, user_id: UUID) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None or user.deleted_at is not None:
            raise NotFoundError("User not found")
        return user

    async def create_user(self, data: UserCreateRequest) -> User:
        existing = await self._repo.get_by_email(data.email)
        if existing:
            raise ConflictError("A user with this email already exists")

        # Create user in INACTIVE state (will be activated on invite accept)
        user = User(
            email=data.email,
            name=data.name,
            role=data.role,
            status=UserStatus.INACTIVE,
            organization_id=UUID(data.organization_id),
            password_hash="",  # No password yet — set on invite accept
        )
        user = await self._repo.create_user(user)

        # Add user-org mapping
        await self._repo.add_user_to_org(
            UserOrganization(
                user_id=user.id,
                organization_id=UUID(data.organization_id),
                role=data.role,
                is_primary=True,
            )
        )

        # Create invitation token
        token = generate_token()
        invitation = Invitation(
            email=data.email,
            organization_id=UUID(data.organization_id),
            role=data.role,
            token_hash=hash_token(token),
            invited_by=user.id,  # Will be overridden by caller if needed
            expires_at=datetime.now(UTC) + timedelta(days=INVITE_TOKEN_EXPIRE_DAYS),
        )
        await self._repo.create_invitation(invitation)

        # TODO: Send invite email via Celery task (Phase 1-A S7 이메일 인프라 구축 후)
        logger.info("user_created_with_invite", user_id=str(user.id), email=data.email)
        return user

    async def update_user(self, user_id: UUID, data: UserUpdateRequest) -> User:
        user = await self.get_user(user_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user
        user = await self._repo.update_user(user, update_data)
        logger.info("user_updated", user_id=str(user_id))
        return user

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.get_user(user_id)
        await self._repo.soft_delete_user(user)
        logger.info("user_deleted", user_id=str(user_id))

    async def get_me(self, user: User) -> dict:
        """Return current user info with org memberships."""
        org_mappings = await self._repo.get_user_org_mappings(user.id)
        orgs = []
        for m in org_mappings:
            org = await self._repo.get_organization_by_id(m.organization_id)
            if org and org.deleted_at is None:
                orgs.append({
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "role": m.role.value,
                    "is_primary": m.is_primary,
                })
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "status": user.status.value,
            "profile_image_url": user.profile_image_url,
            "organizations": orgs,
        }
