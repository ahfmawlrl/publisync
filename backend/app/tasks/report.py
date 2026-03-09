"""Celery task for AI report generation — Phase 3 (F19)."""

import io
import json
import time
from datetime import UTC, datetime

import structlog

from app.tasks import celery_app

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.report.generate_report_task",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    time_limit=300,
    queue="ai",
)
def generate_report_task(self, job_id: str, report_id: str, org_id: str) -> dict:
    """Generate AI report content + PDF asynchronously."""
    from uuid import UUID

    import litellm
    from sqlalchemy import func, select

    from app.core.database import sync_session_factory
    from app.models.ai_usage import AiJob, AiUsageLog
    from app.models.channel import Channel
    from app.models.comment import Comment
    from app.models.content import Content, PublishResult
    from app.models.enums import AiJobStatus, AiTaskType, PublishResultStatus, ReportStatus
    from app.models.report import Report

    session = sync_session_factory()
    try:
        # Mark job as processing
        job = session.get(AiJob, UUID(job_id))
        if not job:
            return {"error": "Job not found"}
        job.status = AiJobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        session.commit()

        # Get report
        report = session.get(Report, UUID(report_id))
        if not report:
            job.status = AiJobStatus.FAILED
            job.error_message = "Report not found"
            session.commit()
            return {"error": "Report not found"}

        # ── Gather analytics data ────────────────────────
        # Platform performance
        platform_stmt = (
            select(
                Channel.platform,
                func.sum(PublishResult.views).label("views"),
                func.sum(PublishResult.likes).label("likes"),
                func.sum(PublishResult.shares).label("shares"),
                func.sum(PublishResult.comments_count).label("comments"),
                func.count(PublishResult.id).label("posts"),
            )
            .join(Channel, PublishResult.channel_id == Channel.id)
            .where(
                PublishResult.organization_id == UUID(org_id),
                PublishResult.status == PublishResultStatus.SUCCESS,
                func.date(PublishResult.created_at) >= report.period_start,
                func.date(PublishResult.created_at) <= report.period_end,
            )
            .group_by(Channel.platform)
        )
        platform_data = [
            {
                "platform": r.platform.value if hasattr(r.platform, "value") else str(r.platform),
                "views": r.views or 0,
                "likes": r.likes or 0,
                "shares": r.shares or 0,
                "comments": r.comments or 0,
                "posts": r.posts or 0,
            }
            for r in session.execute(platform_stmt).all()
        ]

        # Sentiment summary
        sentiment_stmt = (
            select(Comment.sentiment, func.count(Comment.id).label("cnt"))
            .where(
                Comment.organization_id == UUID(org_id),
                func.date(Comment.created_at) >= report.period_start,
                func.date(Comment.created_at) <= report.period_end,
            )
            .group_by(Comment.sentiment)
        )
        sentiment_data = {
            r.sentiment.value if hasattr(r.sentiment, "value") else str(r.sentiment): r.cnt
            for r in session.execute(sentiment_stmt).all()
        }

        # Top contents
        engagement_expr = (
            PublishResult.views + PublishResult.likes
            + PublishResult.shares + PublishResult.comments_count
        )
        top_stmt = (
            select(Content.id, Content.title, func.sum(engagement_expr).label("engagement"))
            .join(PublishResult, PublishResult.content_id == Content.id)
            .where(
                Content.organization_id == UUID(org_id),
                PublishResult.status == PublishResultStatus.SUCCESS,
                func.date(PublishResult.created_at) >= report.period_start,
                func.date(PublishResult.created_at) <= report.period_end,
            )
            .group_by(Content.id, Content.title)
            .order_by(func.sum(engagement_expr).desc())
            .limit(5)
        )
        top_contents = [
            {"title": r.title, "engagement": r.engagement or 0}
            for r in session.execute(top_stmt).all()
        ]

        # ── AI generation ─────────────────────────────────
        data_summary = json.dumps(
            {
                "period": f"{report.period_start} ~ {report.period_end}",
                "platform_performance": platform_data,
                "sentiment_distribution": sentiment_data,
                "top_contents": top_contents,
            },
            ensure_ascii=False,
            indent=2,
        )

        prompt = (
            "다음은 공공기관 소셜 미디어 운영 데이터입니다. "
            "이를 바탕으로 운영 리포트를 작성해주세요.\n\n"
            f"데이터:\n{data_summary}\n\n"
            "다음 JSON 형식으로 리포트를 작성해주세요:\n"
            '{\n  "summary": "요약 (200자 이내)",\n'
            '  "platformPerformance": "플랫폼별 성과 분석",\n'
            '  "topContents": "상위 콘텐츠 분석",\n'
            '  "commentAnalysis": "댓글·여론 분석",\n'
            '  "aiSuggestions": "개선 제안 3~5개"\n}\n\n'
            "반드시 유효한 JSON만 출력하세요."
        )

        start_time = time.time()
        model_used = "gpt-4o"
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        try:
            response = litellm.completion(
                model=model_used,
                messages=[
                    {"role": "system", "content": "You are a public agency social media analytics expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.5,
            )
            response_text = response.choices[0].message.content or ""
            usage = getattr(response, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
                completion_tokens = getattr(usage, "completion_tokens", 0) or 0
                total_tokens = getattr(usage, "total_tokens", 0) or 0
            model_used = getattr(response, "model", model_used) or model_used
        except Exception as ai_exc:
            logger.warning("report_ai_generation_failed", error=str(ai_exc))
            response_text = ""
        processing_time = int((time.time() - start_time) * 1000)

        # Parse AI response
        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            sections = json.loads(response_text)
        except (json.JSONDecodeError, IndexError):
            sections = {
                "summary": response_text or "리포트 생성 중 형식 오류가 발생했습니다.",
                "platformPerformance": "데이터를 기반으로 수동 분석이 필요합니다.",
                "topContents": "상위 콘텐츠 데이터를 확인하세요.",
                "commentAnalysis": "댓글 감성 데이터를 확인하세요.",
                "aiSuggestions": "수동으로 개선점을 검토하세요.",
            }

        # Build structured report content
        content = {
            "summary": {"type": "AI_TEXT", "content": sections.get("summary", "")},
            "platformPerformance": {
                "type": "CHART_DATA",
                "content": sections.get("platformPerformance", ""),
                "data": platform_data,
            },
            "topContents": {
                "type": "TABLE_DATA",
                "content": sections.get("topContents", ""),
                "data": top_contents,
            },
            "commentAnalysis": {
                "type": "CHART_DATA",
                "content": sections.get("commentAnalysis", ""),
                "data": sentiment_data,
            },
            "aiSuggestions": {"type": "AI_TEXT", "content": sections.get("aiSuggestions", "")},
        }

        # Update report
        report.content = content
        report.status = ReportStatus.DRAFT
        report.generated_by = model_used

        # Try to generate PDF
        pdf_url = _generate_pdf(report, org_id)
        if pdf_url:
            report.pdf_url = pdf_url
        session.commit()

        # Mark job complete
        job.status = AiJobStatus.COMPLETED
        job.progress = 100
        job.result = {"report_id": report_id, "pdf_url": pdf_url}
        job.completed_at = datetime.now(UTC)
        session.commit()

        # Log AI usage
        usage_log = AiUsageLog(
            organization_id=UUID(org_id),
            user_id=job.user_id,
            task_type=AiTaskType.REPORT,
            model=model_used,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=0,
            processing_time_ms=processing_time,
            input_summary=f"Report: {report.period_start} ~ {report.period_end}",
            output_summary="Report generated successfully",
        )
        session.add(usage_log)
        session.commit()

        logger.info("report_generation_completed", report_id=report_id, job_id=job_id)
        return {"status": "completed", "report_id": report_id}

    except Exception as exc:
        logger.error("report_generation_failed", job_id=job_id, error=str(exc))
        try:
            job = session.get(AiJob, UUID(job_id))
            if job:
                job.status = AiJobStatus.FAILED
                job.error_message = str(exc)[:500]
                job.completed_at = datetime.now(UTC)
            report_obj = session.get(Report, UUID(report_id))
            if report_obj:
                report_obj.status = ReportStatus.DRAFT
                report_obj.content = {"error": str(exc)[:500]}
            session.commit()
        except Exception:
            session.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        session.close()


def _generate_pdf(report, org_id: str) -> str | None:
    """Generate PDF from report content using WeasyPrint."""
    try:
        from weasyprint import HTML

        from app.core.config import settings
        from app.integrations.storage import _get_client

        sections = report.content or {}
        html_parts = [
            "<html><head><meta charset='utf-8'><style>",
            "body { font-family: sans-serif; padding: 40px; }",
            "h1 { color: #1677ff; }",
            "h2 { color: #333; border-bottom: 1px solid #eee; padding-bottom: 8px; }",
            "</style></head><body>",
            f"<h1>{report.title}</h1>",
            f"<p>기간: {report.period_start} ~ {report.period_end}</p>",
        ]

        section_titles = {
            "summary": "요약",
            "platformPerformance": "플랫폼별 성과",
            "topContents": "주요 콘텐츠",
            "commentAnalysis": "댓글·여론 분석",
            "aiSuggestions": "개선 제안",
        }

        for key, title in section_titles.items():
            section = sections.get(key, {})
            content_text = section.get("content", "") if isinstance(section, dict) else str(section)
            html_parts.append(f"<h2>{title}</h2>")
            html_parts.append(f"<p>{content_text}</p>")

        html_parts.append("</body></html>")
        html_str = "\n".join(html_parts)

        pdf_bytes = HTML(string=html_str).write_pdf()
        pdf_buffer = io.BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        object_name = f"orgs/{org_id}/reports/{report.id}.pdf"
        minio_client = _get_client()
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            pdf_buffer,
            length=len(pdf_bytes),
            content_type="application/pdf",
        )
        return object_name

    except ImportError:
        logger.warning("weasyprint_not_installed")
        return None
    except Exception as e:
        logger.warning("pdf_generation_error", error=str(e))
        return None
