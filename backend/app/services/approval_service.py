"""Approval workflow business logic — S6 (F09)."""

from uuid import UUID

import structlog

from app.core.exceptions import NotFoundError, WorkflowStateConflictError
from app.models.approval import ApprovalHistory, ApprovalRequest, ApprovalWorkflow
from app.models.enums import ApprovalAction, ApprovalStatus, ContentStatus
from app.repositories.approval_repository import ApprovalRepository
from app.repositories.content_repository import ContentRepository

logger = structlog.get_logger()


class ApprovalService:
    def __init__(self, repo: ApprovalRepository, content_repo: ContentRepository | None = None) -> None:
        self._repo = repo
        self._content_repo = content_repo

    async def list_approvals(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
        status: str | None = None,
        content_id: UUID | None = None,
        requested_by: UUID | None = None,
    ) -> tuple[list[ApprovalRequest], int]:
        offset = (page - 1) * limit
        return await self._repo.list_requests(
            org_id, offset=offset, limit=limit, status=status,
            content_id=content_id, requested_by=requested_by,
        )

    async def get_approval(self, request_id: UUID, org_id: UUID) -> ApprovalRequest:
        req = await self._repo.get_by_id(request_id)
        if req is None or req.organization_id != org_id:
            raise NotFoundError("Approval request not found")
        return req

    async def approve(
        self, request_id: UUID, org_id: UUID, reviewer_id: UUID, comment: str | None = None,
    ) -> ApprovalRequest:
        req = await self.get_approval(request_id, org_id)

        if req.status not in (ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW):
            raise WorkflowStateConflictError("Approval request is not in a reviewable state")

        await self._repo.update(req, {"status": ApprovalStatus.APPROVED})

        await self._repo.add_history(ApprovalHistory(
            request_id=req.id,
            organization_id=org_id,
            step=req.current_step,
            action=ApprovalAction.APPROVE,
            reviewer_id=reviewer_id,
            comment=comment,
        ))

        # Update content status to APPROVED
        if self._content_repo:
            content = await self._content_repo.get_by_id(req.content_id)
            if content:
                await self._content_repo.update(content, {"status": ContentStatus.APPROVED})

        logger.info("approval_approved", request_id=str(request_id))
        return req

    async def reject(
        self, request_id: UUID, org_id: UUID, reviewer_id: UUID, comment: str | None = None,
    ) -> ApprovalRequest:
        req = await self.get_approval(request_id, org_id)

        if req.status not in (ApprovalStatus.PENDING_REVIEW, ApprovalStatus.IN_REVIEW):
            raise WorkflowStateConflictError("Approval request is not in a reviewable state")

        await self._repo.update(req, {"status": ApprovalStatus.REJECTED})

        await self._repo.add_history(ApprovalHistory(
            request_id=req.id,
            organization_id=org_id,
            step=req.current_step,
            action=ApprovalAction.REJECT,
            reviewer_id=reviewer_id,
            comment=comment,
        ))

        # Update content status to REJECTED
        if self._content_repo:
            content = await self._content_repo.get_by_id(req.content_id)
            if content:
                await self._content_repo.update(content, {"status": ContentStatus.REJECTED})

        logger.info("approval_rejected", request_id=str(request_id))
        return req

    async def get_workflows(self, org_id: UUID) -> list[ApprovalWorkflow]:
        return await self._repo.list_workflows(org_id)

    async def update_workflow(self, org_id: UUID, data: dict) -> ApprovalWorkflow:
        return await self._repo.upsert_workflow(org_id, data)

    async def count_pending(self, org_id: UUID) -> int:
        return await self._repo.count_pending(org_id)
