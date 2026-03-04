"""Repository for ApprovalWorkflow, ApprovalRequest, ApprovalHistory — S6 (F09)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval import ApprovalHistory, ApprovalRequest, ApprovalWorkflow
from app.models.enums import ApprovalStatus


class ApprovalRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── ApprovalRequest ──────────────────────────────────

    async def get_by_id(self, request_id: UUID) -> ApprovalRequest | None:
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == request_id)
            .options(selectinload(ApprovalRequest.histories))
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requests(
        self,
        org_id: UUID,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[ApprovalRequest], int]:
        base = select(ApprovalRequest).where(ApprovalRequest.organization_id == org_id)
        count_base = select(func.count()).select_from(ApprovalRequest).where(
            ApprovalRequest.organization_id == org_id
        )

        if status:
            base = base.where(ApprovalRequest.status == status)
            count_base = count_base.where(ApprovalRequest.status == status)

        total = (await self._db.execute(count_base)).scalar() or 0
        stmt = base.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_content_id(self, content_id: UUID) -> ApprovalRequest | None:
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.content_id == content_id)
            .order_by(ApprovalRequest.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return result.scalars().first()

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        self._db.add(request)
        await self._db.flush()
        return request

    async def update(self, request: ApprovalRequest, data: dict) -> ApprovalRequest:
        for key, value in data.items():
            setattr(request, key, value)
        await self._db.flush()
        return request

    async def count_pending(self, org_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(ApprovalRequest)
            .where(
                ApprovalRequest.organization_id == org_id,
                ApprovalRequest.status.in_([ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW]),
            )
        )
        result = await self._db.execute(stmt)
        return result.scalar() or 0

    # ── ApprovalHistory ──────────────────────────────────

    async def add_history(self, history: ApprovalHistory) -> None:
        self._db.add(history)
        await self._db.flush()

    # ── ApprovalWorkflow ─────────────────────────────────

    async def get_workflow(self, workflow_id: UUID) -> ApprovalWorkflow | None:
        return await self._db.get(ApprovalWorkflow, workflow_id)

    async def list_workflows(self, org_id: UUID) -> list[ApprovalWorkflow]:
        stmt = (
            select(ApprovalWorkflow)
            .where(ApprovalWorkflow.organization_id == org_id)
            .order_by(ApprovalWorkflow.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_active_workflow(self, org_id: UUID) -> ApprovalWorkflow | None:
        stmt = select(ApprovalWorkflow).where(
            ApprovalWorkflow.organization_id == org_id,
            ApprovalWorkflow.is_active.is_(True),
        )
        result = await self._db.execute(stmt)
        return result.scalars().first()

    async def upsert_workflow(self, org_id: UUID, data: dict) -> ApprovalWorkflow:
        existing = await self.get_active_workflow(org_id)
        if existing:
            for key, value in data.items():
                if value is not None:
                    setattr(existing, key, value)
            await self._db.flush()
            return existing
        else:
            wf = ApprovalWorkflow(
                organization_id=org_id,
                name=data.get("name", "Default Workflow"),
                steps=data.get("steps", []),
                is_active=data.get("is_active", True),
            )
            self._db.add(wf)
            await self._db.flush()
            return wf
