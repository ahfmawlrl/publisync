"""FastAPI dependency injection chain for auth, workspace, and RBAC."""

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.exceptions import (
    AuthenticationError,
    CrossTenantAccessError,
    InsufficientRoleError,
)
from app.core.redis import redis_client
from app.core.security import decode_access_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository


async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Decode JWT, check Redis blacklist, return User ORM object."""
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header")

    token = authorization.removeprefix("Bearer ")
    payload = decode_access_token(token)

    # Redis blacklist check
    jti = payload.get("jti")
    if jti and await redis_client.exists(f"jwt:blacklist:{jti}"):
        raise AuthenticationError("Token has been revoked")

    user_id = UUID(payload["sub"])
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationError("User not found")
    if user.status.value != "ACTIVE":
        raise AuthenticationError("Account is not active")

    return user


class WorkspaceContext:
    """Holds the resolved workspace (organization) context."""

    def __init__(self, org_id: UUID, user: User) -> None:
        self.org_id = org_id
        self.user = user
        self.user_role = user.role


async def get_workspace_context(
    user: User = Depends(get_current_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-Id"),
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceContext:
    """Resolve workspace, verify membership, set RLS session variables."""
    if not x_workspace_id:
        raise CrossTenantAccessError("X-Workspace-Id header is required")

    try:
        org_id = UUID(x_workspace_id)
    except ValueError:
        raise CrossTenantAccessError("X-Workspace-Id must be a valid UUID") from None

    # SA can access any workspace
    if user.role != UserRole.SYSTEM_ADMIN:
        repo = UserRepository(db)
        is_member = await repo.is_org_member(user.id, org_id)
        if not is_member:
            raise CrossTenantAccessError()

    # Set RLS session variables
    await db.execute(text(f"SET LOCAL app.current_org_id = '{org_id}'"))
    await db.execute(text(f"SET LOCAL app.user_role = '{user.role.value}'"))

    return WorkspaceContext(org_id=org_id, user=user)


def require_roles(*roles: UserRole) -> Callable:
    """Factory that returns a dependency checking user role against allowed roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise InsufficientRoleError()
        return user

    return _check
