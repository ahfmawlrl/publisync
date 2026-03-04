"""Report business logic — S18 (F19)."""

import structlog
from datetime import datetime, timezone
from uuid import UUID

from app.models.ai_usage import AiJob
from app.models.enums import AiJobStatus, AiJobType, ReportStatus
from app.models.report import Report
from app.repositories.report_repository import ReportRepository

logger = structlog.get_logger()


class ReportService:
    def __init__(self, repo: ReportRepository) -> None:
        self._repo = repo

    async def list_reports(
        self,
        org_id: UUID,
        period: str | None = None,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Report], int]:
        return await self._repo.list_reports(
            org_id, period=period, status=status, page=page, limit=limit,
        )

    async def generate_report(
        self,
        org_id: UUID,
        user_id: UUID,
        period: str,
        period_start,
        period_end,
        include_sections: list[str] | None = None,
    ) -> tuple[Report, AiJob]:
        """Create report record + AiJob, dispatch Celery task."""
        title = f"{period_start} ~ {period_end} {period} 운영 리포트"
        report = Report(
            organization_id=org_id,
            title=title,
            period=period,
            period_start=period_start,
            period_end=period_end,
            status=ReportStatus.GENERATING,
            content={},
            created_by=user_id,
        )
        report = await self._repo.create(report)

        # Create AiJob for tracking
        job = AiJob(
            organization_id=org_id,
            user_id=user_id,
            job_type=AiJobType.REPORT,
            status=AiJobStatus.PENDING,
            input_params={
                "report_id": str(report.id),
                "period": period,
                "period_start": str(period_start),
                "period_end": str(period_end),
                "include_sections": include_sections,
            },
        )
        self._repo.db.add(job)
        await self._repo.db.flush()
        await self._repo.db.refresh(job)
        await self._repo.db.commit()

        # Dispatch Celery task
        from app.tasks.report import generate_report_task

        generate_report_task.delay(str(job.id), str(report.id), str(org_id))

        logger.info(
            "report_generation_started",
            report_id=str(report.id),
            job_id=str(job.id),
        )
        return report, job

    async def get_report(self, report_id: UUID, org_id: UUID) -> Report | None:
        return await self._repo.get_by_id(report_id, org_id)

    async def update_report(
        self,
        report_id: UUID,
        org_id: UUID,
        title: str | None = None,
        content: dict | None = None,
    ) -> Report | None:
        report = await self._repo.get_by_id(report_id, org_id)
        if not report:
            return None
        if report.status == ReportStatus.FINALIZED:
            return None  # Cannot edit finalized reports

        if title is not None:
            report.title = title
        if content is not None:
            report.content = content
        report = await self._repo.update(report)
        await self._repo.db.commit()
        return report

    async def finalize_report(self, report_id: UUID, org_id: UUID) -> Report | None:
        report = await self._repo.get_by_id(report_id, org_id)
        if not report or report.status == ReportStatus.FINALIZED:
            return None

        report.status = ReportStatus.FINALIZED
        report.finalized_at = datetime.now(timezone.utc)
        report = await self._repo.update(report)
        await self._repo.db.commit()
        logger.info("report_finalized", report_id=str(report_id))
        return report

    async def delete_report(self, report_id: UUID, org_id: UUID) -> bool:
        """Delete a draft report. Cannot delete finalized reports."""
        report = await self._repo.get_by_id(report_id, org_id)
        if not report or report.status == ReportStatus.FINALIZED:
            return False

        await self._repo.db.delete(report)
        await self._repo.db.commit()
        logger.info("report_deleted", report_id=str(report_id))
        return True

    async def get_pdf_url(self, report_id: UUID, org_id: UUID) -> str | None:
        report = await self._repo.get_by_id(report_id, org_id)
        if not report:
            return None
        return report.pdf_url
