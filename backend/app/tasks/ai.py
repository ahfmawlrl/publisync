"""AI queue tasks — sentiment analysis batch processing + async jobs (S18 F03/F15)."""

import structlog
from celery import shared_task

from app.tasks import celery_app

logger = structlog.get_logger()


@shared_task(name="app.tasks.ai.analyze_sentiment_batch", bind=True, max_retries=2)
def analyze_sentiment_batch(self) -> dict:
    """Analyze sentiment for unprocessed comments in batch.

    Runs every 10 minutes via Celery Beat.
    Uses litellm to classify comment sentiment (POSITIVE/NEUTRAL/NEGATIVE/DANGEROUS).
    """
    from datetime import datetime, timezone

    logger.info("analyze_sentiment_batch_start")

    # In production, this would:
    # 1. Query comments WHERE sentiment IS NULL LIMIT 100
    # 2. Batch classify using litellm (max ~50 per request for cost efficiency)
    # 3. UPDATE comment SET sentiment=?, sentiment_confidence=?, keywords=?
    # 4. For DANGEROUS: create notification for AM/AO users
    # 5. Log AI usage to ai_usage_logs

    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "processed": 0,
        "dangerous_found": 0,
    }


@shared_task(name="app.tasks.ai.generate_content_metadata", bind=True, max_retries=2)
def generate_content_metadata(self, content_id: str, task_type: str) -> dict:
    """Generate AI metadata for a specific content (async version).

    Called by service layer when processing takes >10s.
    """
    logger.info("generate_content_metadata_start", content_id=content_id, task_type=task_type)

    # In production, this would:
    # 1. Load content from DB
    # 2. Call litellm with appropriate prompt for task_type
    # 3. Store suggestions in a cache/temp table
    # 4. Send SSE notification to user that AI suggestions are ready

    return {
        "content_id": content_id,
        "task_type": task_type,
        "status": "completed",
    }


# ── S18 — AI Asynchronous Features (F03/F15) ────────────


@celery_app.task(name="generate_subtitles", bind=True, max_retries=2, default_retry_delay=60)
def generate_subtitles_task(self, job_id: str) -> None:
    """Async subtitle generation from video/audio (F03).

    Simulates AI subtitle generation. In production, would use Whisper API or similar.
    Updates AiJob status/progress/result in DB.
    """
    import time
    from datetime import datetime, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    # Sync DB session for Celery
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        job = session.get(AiJob, job_id)
        if not job:
            engine.dispose()
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.progress = 10
            session.commit()

            # Simulate processing stages
            time.sleep(2)
            job.progress = 50
            session.commit()

            time.sleep(2)
            job.progress = 90
            session.commit()

            # Generate mock result (in production: call Whisper/AI service)
            params = job.input_params or {}
            language = params.get("language", "ko")
            result = {
                "subtitles": [
                    {"start": "00:00:00", "end": "00:00:05", "text": f"[{language}] 자막 샘플 1"},
                    {"start": "00:00:05", "end": "00:00:10", "text": f"[{language}] 자막 샘플 2"},
                    {"start": "00:00:10", "end": "00:00:15", "text": f"[{language}] 자막 샘플 3"},
                ],
                "language": language,
                "total_segments": 3,
            }

            job.status = AiJobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            raise self.retry(exc=exc)
        finally:
            engine.dispose()


@celery_app.task(name="extract_shortform", bind=True, max_retries=2, default_retry_delay=60)
def extract_shortform_task(self, job_id: str) -> None:
    """Async shortform clip extraction from long video (F15).

    Simulates AI shortform extraction. In production, would use video analysis + ffmpeg.
    """
    import time
    from datetime import datetime, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        job = session.get(AiJob, job_id)
        if not job:
            engine.dispose()
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.progress = 10
            session.commit()

            params = job.input_params or {}
            count = params.get("count", 3)
            target_duration = params.get("target_duration", 60)
            style = params.get("style", "highlight")

            time.sleep(3)
            job.progress = 60
            session.commit()

            time.sleep(2)
            job.progress = 90
            session.commit()

            # Mock result
            clips = []
            for i in range(count):
                clips.append(
                    {
                        "clip_index": i + 1,
                        "start_time": f"00:{i * 2:02d}:00",
                        "end_time": f"00:{i * 2:02d}:{target_duration:02d}",
                        "title": f"하이라이트 클립 {i + 1}",
                        "score": round(0.95 - i * 0.05, 2),
                        "style": style,
                    }
                )

            result = {
                "clips": clips,
                "total_clips": len(clips),
                "target_duration": target_duration,
                "style": style,
            }

            job.status = AiJobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            raise self.retry(exc=exc)
        finally:
            engine.dispose()


# ── Phase 4 — Thumbnail (F16) ────────────────────────


@celery_app.task(name="generate_thumbnail", bind=True, max_retries=1, default_retry_delay=60)
def generate_thumbnail_task(self, job_id: str) -> None:
    """Async thumbnail generation using AI (F16).

    Analyzes content and generates thumbnail design candidates.
    In production, would call DALL-E/Stable Diffusion for image generation.
    """
    import time
    from datetime import datetime, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    with Session(engine) as session:
        job = session.get(AiJob, job_id)
        if not job:
            engine.dispose()
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            job.progress = 10
            session.commit()

            params = job.input_params or {}
            content_text = params.get("content_text", "")
            style = params.get("style", "modern")
            count = params.get("count", 3)
            aspect_ratio = params.get("aspect_ratio", "16:9")

            # Stage 1: Content analysis
            time.sleep(2)
            job.progress = 30
            session.commit()

            # Stage 2: Generate thumbnail designs (mock)
            time.sleep(3)
            job.progress = 70
            session.commit()

            # Stage 3: Finalize candidates
            time.sleep(1)
            job.progress = 90
            session.commit()

            # Mock thumbnail candidates
            candidates = []
            styles_map = {
                "modern": ["#1890ff", "#ffffff", "#f0f2f5"],
                "classic": ["#2c3e50", "#ecf0f1", "#e74c3c"],
                "minimalist": ["#ffffff", "#333333", "#f5f5f5"],
                "bold": ["#ff4d4f", "#fadb14", "#52c41a"],
            }
            colors = styles_map.get(style, styles_map["modern"])

            for i in range(count):
                candidates.append({
                    "index": i + 1,
                    "layout": ["center-text", "split-layout", "overlay"][i % 3],
                    "colors": colors,
                    "text_overlay": f"썸네일 후보 {i + 1}",
                    "aspect_ratio": aspect_ratio,
                    "style": style,
                    "score": round(0.95 - i * 0.05, 2),
                    "description": f"{style} 스타일의 {aspect_ratio} 썸네일 디자인",
                    "image_url": None,  # Would contain MinIO URL in production
                })

            result = {
                "candidates": candidates,
                "total_candidates": len(candidates),
                "style": style,
                "aspect_ratio": aspect_ratio,
                "fallback_message": "AI 썸네일 생성이 어려운 경우 직접 이미지를 업로드해 주세요.",
            }

            job.status = AiJobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            raise self.retry(exc=exc)
        finally:
            engine.dispose()
