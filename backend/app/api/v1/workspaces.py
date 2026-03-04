"""Workspaces API — 2 endpoints (GET /workspaces, GET /users/me is in users.py)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.org_repository import OrgRepository
from app.schemas.common import ApiResponse
from app.schemas.organization import WorkspaceResponse
from app.services.org_service import OrgService

router = APIRouter()


def _get_org_service(db: AsyncSession = Depends(get_db_session)) -> OrgService:
    return OrgService(OrgRepository(db))


# ── GET /workspaces ──────────────────────────────────────

@router.get("", response_model=ApiResponse[list[WorkspaceResponse]])
async def list_workspaces(
    user: User = Depends(get_current_user),
    service: OrgService = Depends(_get_org_service),
) -> dict:
    workspaces = await service.get_user_workspaces(user.id)
    return {"success": True, "data": workspaces}
