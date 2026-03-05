"""Organization and Agency business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.core.exceptions import ConflictError, NotFoundError
from app.models.user import Agency, Organization
from app.repositories.org_repository import OrgRepository
from app.schemas.organization import AgencyCreateRequest, OrgCreateRequest, OrgUpdateRequest

if TYPE_CHECKING:
    from app.models.enums import UserRole

logger = structlog.get_logger()


class OrgService:
    def __init__(self, repo: OrgRepository) -> None:
        self._repo = repo

    # ── Organization ─────────────────────────────────────

    async def list_orgs(self, page: int = 1, limit: int = 20) -> tuple[list[Organization], int]:
        offset = (page - 1) * limit
        return await self._repo.list_orgs(offset=offset, limit=limit)

    async def get_org(self, org_id: UUID) -> Organization:
        org = await self._repo.get_org_by_id(org_id)
        if org is None or org.deleted_at is not None:
            raise NotFoundError("Organization not found")
        return org

    async def create_org(self, data: OrgCreateRequest) -> Organization:
        existing = await self._repo.get_org_by_slug(data.slug)
        if existing:
            raise ConflictError("An organization with this slug already exists")

        org = Organization(
            name=data.name,
            slug=data.slug,
            plan=data.plan,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            agency_id=UUID(data.agency_id) if data.agency_id else None,
        )
        org = await self._repo.create_org(org)
        logger.info("organization_created", org_id=str(org.id), slug=data.slug)
        return org

    async def update_org(self, org_id: UUID, data: OrgUpdateRequest) -> Organization:
        org = await self.get_org(org_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return org
        org = await self._repo.update_org(org, update_data)
        logger.info("organization_updated", org_id=str(org_id))
        return org

    async def delete_org(self, org_id: UUID) -> None:
        org = await self.get_org(org_id)
        await self._repo.soft_delete_org(org)
        logger.info("organization_deleted", org_id=str(org_id))

    # ── Workspace ────────────────────────────────────────

    async def get_user_workspaces(self, user_id: UUID) -> list[dict]:
        return await self._repo.get_user_workspaces(user_id)

    async def get_badge_counts(self, org_id: UUID, user_role: UserRole | None = None) -> dict:
        # Placeholder — actual counts come from contents/approvals/comments tables (S4+)
        # user_role will be used for role-specific badge logic
        return {
            "pending_approvals": 0,
            "scheduled_posts": 0,
            "unread_comments": 0,
            "unread_notifications": 0,
        }

    # ── Agency ───────────────────────────────────────────

    async def list_agencies(self, page: int = 1, limit: int = 20) -> tuple[list[Agency], int]:
        offset = (page - 1) * limit
        return await self._repo.list_agencies(offset=offset, limit=limit)

    async def create_agency(self, data: AgencyCreateRequest) -> Agency:
        agency = Agency(
            name=data.name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
        )
        agency = await self._repo.create_agency(agency)
        logger.info("agency_created", agency_id=str(agency.id))
        return agency

    # ── Roles ────────────────────────────────────────────

    async def list_roles(self) -> list:
        return await self._repo.list_roles()
