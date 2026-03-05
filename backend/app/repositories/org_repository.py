"""Repository for Organization and Agency tables."""

from datetime import UTC
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Agency, Organization, Role, UserOrganization


class OrgRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Organization ─────────────────────────────────────

    async def get_org_by_id(self, org_id: UUID) -> Organization | None:
        return await self._db.get(Organization, org_id)

    async def get_org_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug, Organization.deleted_at.is_(None))
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_orgs(self, offset: int = 0, limit: int = 20) -> tuple[list[Organization], int]:
        count_stmt = select(func.count()).select_from(Organization).where(Organization.deleted_at.is_(None))
        total = (await self._db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Organization)
            .where(Organization.deleted_at.is_(None))
            .order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_org(self, org: Organization) -> Organization:
        self._db.add(org)
        await self._db.flush()
        return org

    async def update_org(self, org: Organization, data: dict) -> Organization:
        for key, value in data.items():
            if value is not None:
                setattr(org, key, value)
        await self._db.flush()
        return org

    async def soft_delete_org(self, org: Organization) -> None:
        from datetime import datetime
        org.deleted_at = datetime.now(UTC)
        await self._db.flush()

    # ── Workspace queries ────────────────────────────────

    async def get_user_workspaces(self, user_id: UUID) -> list[dict]:
        stmt = (
            select(
                Organization.id,
                Organization.name,
                Organization.slug,
                UserOrganization.role,
                UserOrganization.is_primary,
            )
            .join(UserOrganization, UserOrganization.organization_id == Organization.id)
            .where(
                UserOrganization.user_id == user_id,
                Organization.deleted_at.is_(None),
            )
        )
        result = await self._db.execute(stmt)
        return [
            {
                "id": str(row.id),
                "name": row.name,
                "slug": row.slug,
                "role": row.role.value,
                "is_primary": row.is_primary,
            }
            for row in result.all()
        ]

    # ── Agency ───────────────────────────────────────────

    async def list_agencies(self, offset: int = 0, limit: int = 20) -> tuple[list[Agency], int]:
        count_stmt = select(func.count()).select_from(Agency)
        total = (await self._db.execute(count_stmt)).scalar() or 0

        stmt = select(Agency).order_by(Agency.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def create_agency(self, agency: Agency) -> Agency:
        self._db.add(agency)
        await self._db.flush()
        return agency

    # ── Role ─────────────────────────────────────────────

    async def list_roles(self) -> list[Role]:
        stmt = select(Role).order_by(Role.name)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
