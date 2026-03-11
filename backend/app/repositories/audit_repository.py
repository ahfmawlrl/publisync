"""Repository for AuditLog — S12 (F14). INSERT-ONLY table."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog
from app.models.enums import AuditAction


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_logs(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
        action: str | None = None,
        resource_type: str | None = None,
        actor_id: UUID | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        base = select(AuditLog).where(AuditLog.organization_id == org_id)
        count_base = select(func.count()).select_from(AuditLog).where(
            AuditLog.organization_id == org_id
        )

        if action:
            base = base.where(AuditLog.action == action)
            count_base = count_base.where(AuditLog.action == action)
        if resource_type:
            base = base.where(AuditLog.resource_type == resource_type)
            count_base = count_base.where(AuditLog.resource_type == resource_type)
        if actor_id:
            base = base.where(AuditLog.actor_id == actor_id)
            count_base = count_base.where(AuditLog.actor_id == actor_id)
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            base = base.where(AuditLog.created_at >= start_dt)
            count_base = count_base.where(AuditLog.created_at >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            base = base.where(AuditLog.created_at <= end_dt)
            count_base = count_base.where(AuditLog.created_at <= end_dt)

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = (
            base.options(selectinload(AuditLog.actor))
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_log(self, log_id: UUID) -> AuditLog | None:
        return await self._db.get(AuditLog, log_id)

    async def create_log(self, log: AuditLog) -> AuditLog:
        """INSERT only — audit logs are immutable."""
        self._db.add(log)
        await self._db.flush()
        await self._db.refresh(log)
        return log

    async def export_logs(
        self,
        org_id: UUID,
        start_date: str,
        end_date: str,
        actions: list[str] | None = None,
    ) -> list[AuditLog]:
        """Return all matching logs for CSV/PDF export."""
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        stmt = select(AuditLog).where(
            AuditLog.organization_id == org_id,
            AuditLog.created_at >= start_dt,
            AuditLog.created_at <= end_dt,
        )

        if actions:
            action_enums = [AuditAction(a) for a in actions]
            stmt = stmt.where(AuditLog.action.in_(action_enums))

        stmt = stmt.order_by(AuditLog.created_at.desc())
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
