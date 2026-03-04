"""Audit log business logic — S12 (F14)."""

import csv
import io
import structlog
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.models.audit import AuditLog
from app.models.enums import AuditAction, UserRole
from app.repositories.audit_repository import AuditRepository

logger = structlog.get_logger()


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    async def list_logs(
        self,
        org_id: UUID,
        page: int = 1,
        limit: int = 20,
        action: str | None = None,
        resource_type: str | None = None,
        actor_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        offset = (page - 1) * limit
        actor_uuid = UUID(actor_id) if actor_id else None
        return await self._repo.list_logs(
            org_id,
            offset=offset,
            limit=limit,
            action=action,
            resource_type=resource_type,
            actor_id=actor_uuid,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_log(self, log_id: UUID, org_id: UUID) -> AuditLog:
        log = await self._repo.get_log(log_id)
        if log is None or log.organization_id != org_id:
            raise NotFoundError("감사 로그를 찾을 수 없습니다.")
        return log

    async def record_action(
        self,
        org_id: UUID,
        actor_id: UUID | None,
        actor_role: UserRole | None,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: UUID | None = None,
    ) -> AuditLog:
        """Create an immutable audit log entry. Reusable from any service."""
        log = AuditLog(
            organization_id=org_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        log = await self._repo.create_log(log)
        logger.info(
            "audit_recorded",
            action=action.value,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
        )
        return log

    async def export_logs(
        self,
        org_id: UUID,
        format: str,
        start_date: str,
        end_date: str,
        actions: list[str] | None = None,
    ) -> str:
        """Export audit logs as CSV string. PDF can be added later."""
        logs = await self._repo.export_logs(org_id, start_date, end_date, actions)

        if format == "csv":
            return self._generate_csv(logs)

        # Default to CSV; PDF generation can be added in a future sprint
        return self._generate_csv(logs)

    @staticmethod
    def _generate_csv(logs: list[AuditLog]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID",
            "시간",
            "액터 ID",
            "액터 역할",
            "액션",
            "리소스 유형",
            "리소스 ID",
            "변경 내용",
            "IP 주소",
            "요청 ID",
        ])
        for log in logs:
            writer.writerow([
                str(log.id),
                str(log.created_at),
                str(log.actor_id) if log.actor_id else "",
                log.actor_role.value if log.actor_role else "",
                log.action.value,
                log.resource_type,
                str(log.resource_id) if log.resource_id else "",
                str(log.changes) if log.changes else "",
                log.ip_address or "",
                str(log.request_id) if log.request_id else "",
            ])
        return output.getvalue()
