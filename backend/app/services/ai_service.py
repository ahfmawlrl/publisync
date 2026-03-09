"""AI business logic — S11 (F02).

Generates titles, descriptions, and hashtags using litellm,
then logs usage to ai_usage_logs for cost tracking.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

from app.integrations.ai import PROMPTS, generate_text
from app.models.ai_usage import AiUsageLog

if TYPE_CHECKING:
    from app.models.ai_usage import AiJob
    from app.schemas.ai import AiTranslateResponse
from app.models.enums import AiTaskType
from app.repositories.ai_usage_repository import AiUsageRepository
from app.schemas.ai import (
    AiContentReviewIssue,
    AiContentReviewResponse,
    AiGenerateResponse,
    AiSuggestion,
    AiUsageResponse,
)

logger = structlog.get_logger()


class AiService:
    def __init__(self, repo: AiUsageRepository) -> None:
        self._repo = repo

    # ── Public API ────────────────────────────────────────────

    async def generate_title(
        self,
        content_text: str,
        platform: str | None = None,
        language: str = "ko",
        count: int = 3,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Generate title suggestions for the given content."""
        prompt = self._build_prompt(content_text, platform, language, count, task="title")
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["TITLE"],
            task_type=AiTaskType.TITLE,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    async def generate_description(
        self,
        content_text: str,
        platform: str | None = None,
        language: str = "ko",
        count: int = 1,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Generate description suggestions for the given content."""
        prompt = self._build_prompt(content_text, platform, language, count, task="description")
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["DESCRIPTION"],
            task_type=AiTaskType.DESCRIPTION,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    async def generate_hashtags(
        self,
        content_text: str,
        platform: str | None = None,
        language: str = "ko",
        count: int = 5,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Generate hashtag suggestions for the given content."""
        prompt = self._build_prompt(content_text, platform, language, count, task="hashtag")
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["HASHTAG"],
            task_type=AiTaskType.HASHTAG,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    # ── S17 — AI Synchronous Features (F05/F17/F21) ────────

    async def generate_reply(
        self,
        comment_text: str,
        content_context: str | None,
        tone: str,
        count: int,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Generate reply drafts for a comment (F05)."""
        prompt = f"원문 댓글:\n{comment_text}"
        if content_context:
            prompt += f"\n\n관련 콘텐츠:\n{content_context}"
        prompt += f"\n\n톤: {tone}\n{count}개의 답글 초안을 작성하세요."
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["GENERATE_REPLY"],
            task_type=AiTaskType.COMMENT_REPLY,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    async def tone_transform(
        self,
        content_text: str,
        target_platform: str,
        target_tone: str,
        count: int,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Transform content tone for a target platform (F17)."""
        prompt = (
            f"원문:\n{content_text}\n\n"
            f"대상 플랫폼: {target_platform}\n"
            f"대상 톤: {target_tone}\n"
            f"{count}개의 변환 결과를 생성하세요."
        )
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["TONE_TRANSFORM"],
            task_type=AiTaskType.TONE_CONVERT,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    async def content_review(
        self,
        content_text: str,
        check_spelling: bool,
        check_sensitivity: bool,
        check_bias: bool,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiContentReviewResponse:
        """Review content for issues — spelling, sensitivity, bias (F21)."""
        checks: list[str] = []
        if check_spelling:
            checks.append("맞춤법 검사")
        if check_sensitivity:
            checks.append("민감 정보 검출")
        if check_bias:
            checks.append("편향/차별 표현 검출")

        prompt = (
            f"콘텐츠:\n{content_text}\n\n"
            f"검사 항목: {', '.join(checks)}\n"
            "발견된 문제를 JSON 배열로 반환하세요."
        )

        result = await generate_text(
            prompt=prompt,
            system_prompt=PROMPTS["CONTENT_REVIEW"],
            model="gpt-4o-mini",
            max_tokens=1000,
            temperature=0.3,
        )

        # Parse issues from AI response
        issues = self._parse_review_issues(result["content"])

        # Log usage
        await self._log_usage(
            org_id=org_id,
            user_id=user_id,
            task_type=AiTaskType.CONTENT_REVIEW,
            model=result["model"],
            usage=result["usage"],
            is_fallback=result.get("is_fallback", False),
            error=result.get("error"),
            input_summary=prompt[:500],
            output_summary=result["content"][:500] if result["content"] else None,
        )

        return AiContentReviewResponse(
            confidence=0.85 if issues else 0.5,
            model=result["model"],
            issues=issues,
            summary=(
                f"{len(issues)}건의 문제가 발견되었습니다."
                if issues
                else "검수 완료: 문제가 발견되지 않았습니다."
            ),
            usage=result["usage"],
            processing_time_ms=result["processing_time_ms"],
            error=result.get("error"),
        )

    async def suggest_effects(
        self,
        content_text: str,
        content_type: str,
        count: int,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Suggest emojis and sound effects for content (F03)."""
        prompt = (
            f"콘텐츠:\n{content_text}\n\n"
            f"콘텐츠 유형: {content_type}\n"
            f"{count}개의 이모지/효과음을 추천하세요."
        )
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["SUGGEST_EFFECTS"],
            task_type=AiTaskType.SUGGEST_EFFECTS,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    async def improve_template(
        self,
        template_text: str,
        purpose: str,
        count: int,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiGenerateResponse:
        """Improve a reply template for better communication (F05)."""
        prompt = (
            f"기존 템플릿:\n{template_text}\n\n"
            f"용도: {purpose}\n"
            f"{count}개의 개선안을 제안하세요."
        )
        return await self._generate_and_log(
            prompt=prompt,
            system_prompt=PROMPTS["IMPROVE_TEMPLATE"],
            task_type=AiTaskType.IMPROVE_TEMPLATE,
            org_id=org_id,
            user_id=user_id,
            count=count,
        )

    # ── S18 — AI Asynchronous Features (F03/F15) ────────────

    async def create_subtitle_job(
        self,
        org_id: UUID,
        user_id: UUID,
        media_asset_id: UUID,
        language: str,
        include_timestamps: bool,
    ) -> AiJob:
        """Create async subtitle generation job."""
        from app.models.ai_usage import AiJob
        from app.models.enums import AiJobStatus, AiJobType

        job = AiJob(
            organization_id=org_id,
            user_id=user_id,
            job_type=AiJobType.SUBTITLE,
            status=AiJobStatus.PENDING,
            input_params={
                "media_asset_id": str(media_asset_id),
                "language": language,
                "include_timestamps": include_timestamps,
            },
            media_asset_id=media_asset_id if media_asset_id else None,
        )
        self._repo.db.add(job)
        await self._repo.db.flush()

        # Dispatch Celery task
        from app.tasks.ai import generate_subtitles_task

        generate_subtitles_task.delay(str(job.id))
        return job

    async def create_shortform_job(
        self,
        org_id: UUID,
        user_id: UUID,
        media_asset_id: UUID,
        target_duration: int,
        count: int,
        style: str,
    ) -> AiJob:
        """Create async shortform extraction job."""
        from app.models.ai_usage import AiJob
        from app.models.enums import AiJobStatus, AiJobType

        job = AiJob(
            organization_id=org_id,
            user_id=user_id,
            job_type=AiJobType.SHORTFORM,
            status=AiJobStatus.PENDING,
            input_params={
                "media_asset_id": str(media_asset_id),
                "target_duration": target_duration,
                "count": count,
                "style": style,
            },
            media_asset_id=media_asset_id if media_asset_id else None,
        )
        self._repo.db.add(job)
        await self._repo.db.flush()

        from app.tasks.ai import extract_shortform_task

        extract_shortform_task.delay(str(job.id))
        return job

    async def get_job_status(self, job_id: str, org_id: UUID) -> AiJob | None:
        """Get async job status by ID."""
        from uuid import UUID as PyUUID

        from sqlalchemy import select

        from app.models.ai_usage import AiJob

        stmt = select(AiJob).where(
            AiJob.id == PyUUID(str(job_id)),
            AiJob.organization_id == org_id,
        )
        result = await self._repo.db.execute(stmt)
        return result.scalar_one_or_none()

    async def confirm_shortform(
        self, job_id: str, org_id: UUID, selected_clips: list[dict]
    ) -> AiJob:
        """Confirm selected shortform clips for a completed extraction job."""
        from datetime import datetime, timezone
        from uuid import UUID as PyUUID

        from sqlalchemy import select

        from app.models.ai_usage import AiJob

        stmt = select(AiJob).where(
            AiJob.id == PyUUID(str(job_id)),
            AiJob.organization_id == org_id,
        )
        result = await self._repo.db.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("작업을 찾을 수 없습니다.")

        # Update job result with confirmed clips
        existing_result = job.result or {}
        existing_result["confirmed_clips"] = selected_clips
        existing_result["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        job.result = existing_result
        job.status = "CONFIRMED"

        await self._repo.db.commit()
        await self._repo.db.refresh(job)

        logger.info(
            "shortform_confirmed",
            job_id=job_id,
            clip_count=len(selected_clips),
        )
        return job

    async def get_usage_stats(
        self, org_id: UUID
    ) -> AiUsageResponse:
        """Return aggregated AI usage statistics for an organization."""
        stats = await self._repo.get_usage_stats(org_id)
        return AiUsageResponse(
            organization_id=str(org_id),
            total_requests=stats["total_requests"],
            total_tokens=stats["total_tokens"],
            estimated_cost=stats["estimated_cost"],
            by_task_type=stats["by_task_type"],
        )

    # ── Private helpers ───────────────────────────────────────

    def _build_prompt(
        self,
        content_text: str,
        platform: str | None,
        language: str,
        count: int,
        task: str,
    ) -> str:
        """Build the user prompt sent to the AI model."""
        parts = [f"본문:\n{content_text}"]

        if platform:
            parts.append(f"대상 플랫폼: {platform}")

        parts.append(f"언어: {language}")

        if task == "title":
            parts.append(f"{count}개의 제목 후보를 생성하세요.")
        elif task == "description":
            parts.append(f"{count}개의 설명문을 생성하세요.")
        elif task == "hashtag":
            parts.append(f"{count}개의 해시태그를 생성하세요.")

        return "\n".join(parts)

    async def _generate_and_log(
        self,
        prompt: str,
        system_prompt: str,
        task_type: AiTaskType,
        org_id: UUID | None,
        user_id: UUID | None,
        count: int,
    ) -> AiGenerateResponse:
        """Call AI, parse suggestions, log usage, return response."""
        result = await generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            model="gpt-4o-mini",
            max_tokens=500,
            temperature=0.7,
        )

        error = result.get("error")
        is_fallback = result.get("is_fallback", False)

        # Parse suggestions from AI response content
        suggestions = self._parse_suggestions(result["content"], count)
        confidence = max((s.score for s in suggestions), default=0.0) if suggestions else 0.0

        # Log usage (fire-and-forget style, but within same transaction)
        await self._log_usage(
            org_id=org_id,
            user_id=user_id,
            task_type=task_type,
            model=result["model"],
            usage=result["usage"],
            is_fallback=is_fallback,
            error=error,
            input_summary=prompt[:500] if prompt else None,
            output_summary=result["content"][:500] if result["content"] else None,
        )

        return AiGenerateResponse(
            isAiGenerated=True,
            confidence=confidence,
            fallbackAvailable=True,
            model=result["model"],
            suggestions=suggestions,
            usage=result["usage"],
            processing_time_ms=result["processing_time_ms"],
            error=error,
        )

    def _parse_suggestions(self, raw_content: str, count: int) -> list[AiSuggestion]:
        """Parse AI response content into structured suggestions.

        Attempts JSON parsing first, falls back to line-based parsing.
        """
        if not raw_content:
            return []

        # Try JSON array parsing
        try:
            # Find JSON array in the response (may be wrapped in markdown code block)
            content = raw_content.strip()
            if "```" in content:
                # Extract content between code fences
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    content = content[start:end]

            data = json.loads(content)
            if isinstance(data, list):
                suggestions = []
                for item in data[:count]:
                    if isinstance(item, dict):
                        suggestions.append(
                            AiSuggestion(
                                content=str(item.get("content", "")),
                                score=float(item.get("score", 0.8)),
                            )
                        )
                    elif isinstance(item, str):
                        suggestions.append(AiSuggestion(content=item, score=0.8))
                return suggestions
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

        # Fallback: line-based parsing
        lines = [line.strip() for line in raw_content.strip().split("\n") if line.strip()]
        suggestions = []
        for line in lines[:count]:
            # Remove numbering (e.g., "1. ", "- ")
            cleaned = line.lstrip("0123456789.-) ").strip()
            if cleaned:
                suggestions.append(AiSuggestion(content=cleaned, score=0.75))

        return suggestions

    def _parse_review_issues(self, raw_content: str) -> list[AiContentReviewIssue]:
        """Parse content review response into structured issues."""
        if not raw_content:
            return []

        try:
            content = raw_content.strip()
            if "```" in content:
                # Extract JSON array from markdown code block
                start = content.find("[")
                end = content.rfind("]") + 1
                if start >= 0 and end > start:
                    content = content[start:end]

            data = json.loads(content)
            if isinstance(data, list):
                return [
                    AiContentReviewIssue(
                        issue=str(item.get("issue", "")),
                        severity=str(item.get("severity", "LOW")),
                        location=item.get("location"),
                        suggestion=str(item.get("suggestion", "")),
                        score=float(item.get("score", 0.8)),
                    )
                    for item in data
                    if isinstance(item, dict)
                ]
        except (json.JSONDecodeError, ValueError):
            pass

        return []

    async def _log_usage(
        self,
        org_id: UUID | None,
        user_id: UUID | None,
        task_type: AiTaskType,
        model: str,
        usage: dict,
        is_fallback: bool,
        error: str | None,
        input_summary: str | None = None,
        output_summary: str | None = None,
    ) -> None:
        """Persist AI usage metrics to the database."""
        if org_id is None:
            logger.warning("ai_usage_log_skipped", reason="no org_id")
            return

        try:
            log = AiUsageLog(
                organization_id=org_id,
                user_id=user_id,
                task_type=task_type,
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                estimated_cost=usage.get("estimated_cost", 0.0),
                processing_time_ms=usage.get("processing_time_ms"),
                input_summary=input_summary,
                output_summary=output_summary,
                is_fallback=is_fallback,
                error_message=error,
            )
            await self._repo.create_log(log)
        except Exception as exc:
            # Usage logging failure should not break the main flow
            logger.error("ai_usage_log_failed", error=str(exc))

    # ── Phase 3 — Optimal Time (F20) ─────────────────────

    async def recommend_optimal_time(
        self,
        content_text: str,
        platforms: list[str],
        org_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Recommend optimal posting time using AI."""
        prompt = (
            "다음 콘텐츠의 최적 게시 시간을 추천해주세요.\n\n"
            f"콘텐츠:\n{content_text[:2000]}\n\n"
            f"대상 플랫폼: {', '.join(platforms) if platforms else '전체'}\n\n"
            "다음 JSON 형식으로 응답해주세요:\n"
            '[{"day_of_week": "요일(MON/TUE/...)", '
            '"time_range": "HH:00~HH:00", '
            '"reason": "추천 사유", '
            '"confidence": 0.0~1.0}]\n\n'
            "최대 3개까지 추천하세요. 반드시 유효한 JSON 배열만 출력하세요."
        )

        result = await generate_text(
            prompt=prompt,
            system_prompt=PROMPTS.get("CONTENT_REVIEW", "You are a social media scheduling expert."),
            model="gpt-4o-mini",
            max_tokens=800,
            temperature=0.5,
        )

        optimal_times = []
        try:
            response_text = result.get("content", "")
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                optimal_times = parsed[:3]
        except (json.JSONDecodeError, IndexError):
            optimal_times = []

        # Log AI usage
        await self._log_usage(
            org_id=org_id,
            user_id=user_id,
            task_type=AiTaskType.PREDICTION,
            model=result["model"],
            usage=result["usage"],
            is_fallback=result.get("is_fallback", False),
            error=result.get("error"),
            input_summary=prompt[:500],
            output_summary=result["content"][:500] if result["content"] else None,
        )

        return {
            "isAiGenerated": True,
            "confidence": result.get("confidence", 0.7),
            "fallbackAvailable": True,
            "model": result.get("model", "gpt-4o-mini"),
            "optimal_times": optimal_times,
            "usage": result.get("usage", {}),
            "processing_time_ms": result.get("processing_time_ms", 0),
            "error": result.get("error"),
        }

    # ── Phase 4 — Thumbnail (F16) + Translation (F22) ────

    async def create_thumbnail_job(
        self,
        org_id: UUID,
        user_id: UUID,
        content_text: str,
        style: str,
        count: int,
        aspect_ratio: str,
    ) -> AiJob:
        """Create async thumbnail generation job (F16)."""
        from app.models.ai_usage import AiJob
        from app.models.enums import AiJobStatus, AiJobType

        job = AiJob(
            organization_id=org_id,
            user_id=user_id,
            job_type=AiJobType.THUMBNAIL,
            status=AiJobStatus.PENDING,
            input_params={
                "content_text": content_text[:2000],
                "style": style,
                "count": count,
                "aspect_ratio": aspect_ratio,
            },
        )
        self._repo.db.add(job)
        await self._repo.db.flush()

        from app.tasks.ai import generate_thumbnail_task

        generate_thumbnail_task.delay(str(job.id))
        return job

    async def translate(
        self,
        content_text: str,
        target_language: str,
        source_language: str,
        preserve_formatting: bool,
        org_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> AiTranslateResponse:
        """Translate content synchronously (F22, < 10s)."""
        from app.schemas.ai import AiTranslateResponse

        LANG_NAMES = {
            "en": "영어(English)",
            "zh": "중국어(中文)",
            "ja": "일본어(日本語)",
            "vi": "베트남어(Tiếng Việt)",
        }
        lang_name = LANG_NAMES.get(target_language, target_language)

        prompt = (
            f"다음 {source_language} 콘텐츠를 {lang_name}로 번역하세요.\n\n"
            f"원문:\n{content_text}\n\n"
        )
        if preserve_formatting:
            prompt += "원문의 줄바꿈, 목록, 제목 등 서식을 유지하세요.\n"
        prompt += (
            "반드시 다음 JSON 형식으로만 응답하세요:\n"
            '{"translated_text": "번역된 텍스트", "notes": "번역 시 참고사항"}'
        )

        result = await generate_text(
            prompt=prompt,
            system_prompt=PROMPTS["TRANSLATE"],
            model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse translation result
        translated_text = ""
        notes = ""
        try:
            import json as _json

            response_text = result.get("content", "")
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            parsed = _json.loads(response_text)
            translated_text = parsed.get("translated_text", "")
            notes = parsed.get("notes", "")
        except (json.JSONDecodeError, IndexError, KeyError):
            translated_text = result.get("content", "")

        # Log usage
        await self._log_usage(
            org_id=org_id,
            user_id=user_id,
            task_type=AiTaskType.TRANSLATION,
            model=result["model"],
            usage=result["usage"],
            is_fallback=result.get("is_fallback", False),
            error=result.get("error"),
            input_summary=prompt[:500],
            output_summary=translated_text[:500] if translated_text else None,
        )

        return AiTranslateResponse(
            confidence=0.85 if translated_text else 0.0,
            model=result["model"],
            translated_text=translated_text,
            target_language=target_language,
            source_language=source_language,
            notes=notes,
            usage=result["usage"],
            processing_time_ms=result["processing_time_ms"],
            error=result.get("error"),
        )
