"""Repository for AiUsageLog — S11 (F02)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage import AiUsageLog


class AiUsageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_log(self, log: AiUsageLog) -> AiUsageLog:
        """Persist a single AI usage log entry."""
        self._db.add(log)
        await self._db.flush()
        return log

    async def get_usage_stats(
        self,
        org_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Return aggregated AI usage statistics for an organization.

        Returns:
            {
                "total_requests": int,
                "total_tokens": int,
                "estimated_cost": float,
                "by_task_type": [
                    {"task_type": str, "request_count": int, "total_tokens": int, "estimated_cost": float},
                    ...
                ]
            }
        """
        # Base filter
        base_filter = [AiUsageLog.organization_id == org_id]
        if start_date:
            base_filter.append(AiUsageLog.created_at >= start_date)
        if end_date:
            base_filter.append(AiUsageLog.created_at <= end_date)

        # Overall totals
        totals_stmt = select(
            func.count().label("total_requests"),
            func.coalesce(func.sum(AiUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AiUsageLog.estimated_cost), Decimal("0")).label("estimated_cost"),
        ).where(*base_filter)

        totals_result = await self._db.execute(totals_stmt)
        totals_row = totals_result.one()

        # Per task_type breakdown
        by_type_stmt = (
            select(
                AiUsageLog.task_type,
                func.count().label("request_count"),
                func.coalesce(func.sum(AiUsageLog.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(AiUsageLog.estimated_cost), Decimal("0")).label("estimated_cost"),
            )
            .where(*base_filter)
            .group_by(AiUsageLog.task_type)
            .order_by(func.count().desc())
        )

        by_type_result = await self._db.execute(by_type_stmt)
        by_task_type = [
            {
                "task_type": row.task_type.value if hasattr(row.task_type, "value") else str(row.task_type),
                "request_count": row.request_count,
                "total_tokens": row.total_tokens,
                "estimated_cost": float(row.estimated_cost),
            }
            for row in by_type_result.all()
        ]

        return {
            "total_requests": totals_row.total_requests,
            "total_tokens": totals_row.total_tokens,
            "estimated_cost": float(totals_row.estimated_cost),
            "by_task_type": by_task_type,
        }
