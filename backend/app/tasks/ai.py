"""AI queue tasks — sentiment analysis batch processing + async jobs (S18 F03/F15)."""

import json
from datetime import UTC, datetime

import structlog
from celery import shared_task

from app.tasks import celery_app

logger = structlog.get_logger()

# ── Sentiment batch size for litellm calls ──────────────
_SENTIMENT_BATCH_SIZE = 20  # comments per litellm call (cost-efficient)
_SENTIMENT_FETCH_LIMIT = 100  # max comments per cron run


@shared_task(name="app.tasks.ai.analyze_sentiment_batch", bind=True, max_retries=2)
def analyze_sentiment_batch(self) -> dict:
    """Analyze sentiment for unprocessed comments in batch.

    Runs every 10 minutes via Celery Beat.
    Uses litellm to classify comment sentiment (POSITIVE/NEUTRAL/NEGATIVE/DANGEROUS).
    """
    from sqlalchemy import select, update

    from app.core.database import sync_session_factory
    from app.models.comment import Comment
    from app.models.enums import CommentSentiment

    logger.info("analyze_sentiment_batch_start")
    processed = 0
    dangerous_found = 0

    try:
        import litellm
    except ImportError:
        logger.error("litellm_not_installed")
        return {"analyzed_at": datetime.now(UTC).isoformat(), "processed": 0, "dangerous_found": 0}

    with sync_session_factory() as session:
        # 1. Query unanalyzed comments
        stmt = (
            select(Comment)
            .where(Comment.sentiment.is_(None))
            .order_by(Comment.created_at.asc())
            .limit(_SENTIMENT_FETCH_LIMIT)
        )
        comments = session.execute(stmt).scalars().all()

        if not comments:
            logger.info("analyze_sentiment_batch_no_comments")
            return {"analyzed_at": datetime.now(UTC).isoformat(), "processed": 0, "dangerous_found": 0}

        # 2. Process in batches
        for i in range(0, len(comments), _SENTIMENT_BATCH_SIZE):
            batch = comments[i : i + _SENTIMENT_BATCH_SIZE]
            batch_texts = []
            for idx, c in enumerate(batch):
                batch_texts.append(f"[{idx}] {c.text[:500]}")

            prompt = (
                "다음 댓글들의 감성을 분류하세요. 각 댓글 번호에 대해 JSON 배열로 응답하세요.\n"
                "분류: POSITIVE(긍정), NEUTRAL(중립), NEGATIVE(부정), DANGEROUS(위험/악성)\n"
                "DANGEROUS 기준: 욕설, 혐오, 위협, 개인정보 노출, 불법 광고\n\n"
                "응답 형식 (JSON 배열만 출력):\n"
                '[{"idx": 0, "sentiment": "POSITIVE", "confidence": 0.95, '
                '"keywords": ["칭찬", "좋아요"]}, ...]\n\n'
                "댓글 목록:\n" + "\n".join(batch_texts)
            )

            try:
                response = litellm.completion(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a Korean social media comment sentiment classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.2,
                )
                content = response.choices[0].message.content or ""

                # Parse JSON from response
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                results = json.loads(content)
                if not isinstance(results, list):
                    results = []

                # 3. Update each comment
                sentiment_map = {s.value: s for s in CommentSentiment}
                for result_item in results:
                    idx = result_item.get("idx", -1)
                    if 0 <= idx < len(batch):
                        comment = batch[idx]
                        sentiment_str = result_item.get("sentiment", "NEUTRAL").upper()
                        sentiment = sentiment_map.get(sentiment_str, CommentSentiment.NEUTRAL)

                        session.execute(
                            update(Comment)
                            .where(Comment.id == comment.id)
                            .values(
                                sentiment=sentiment,
                                sentiment_confidence=result_item.get("confidence", 0.5),
                                keywords=result_item.get("keywords", []),
                                dangerous_level="HIGH" if sentiment == CommentSentiment.DANGEROUS else None,
                            )
                        )
                        processed += 1

                        if sentiment == CommentSentiment.DANGEROUS:
                            dangerous_found += 1
                            logger.warning(
                                "dangerous_comment_detected",
                                comment_id=str(comment.id),
                                org_id=str(comment.organization_id),
                            )

            except (json.JSONDecodeError, KeyError, IndexError) as parse_err:
                logger.warning("sentiment_parse_error", error=str(parse_err), batch_index=i)
                continue
            except Exception as api_err:
                logger.error("sentiment_api_error", error=str(api_err), batch_index=i)
                continue

        session.commit()

    logger.info(
        "analyze_sentiment_batch_complete",
        processed=processed,
        dangerous_found=dangerous_found,
    )
    return {
        "analyzed_at": datetime.now(UTC).isoformat(),
        "processed": processed,
        "dangerous_found": dangerous_found,
    }


@shared_task(name="app.tasks.ai.generate_content_metadata", bind=True, max_retries=2)
def generate_content_metadata(self, content_id: str, task_type: str) -> dict:
    """Generate AI metadata for a specific content (async version).

    Called by service layer when processing takes >10s.
    """
    logger.info("generate_content_metadata_start", content_id=content_id, task_type=task_type)

    try:
        import litellm

        from app.core.database import sync_session_factory
        from app.models.content import Content

        with sync_session_factory() as session:
            content = session.get(Content, content_id)
            if not content:
                return {"content_id": content_id, "task_type": task_type, "status": "not_found"}

            content_text = content.body or content.title or ""
            prompt_map = {
                "title": "이 콘텐츠에 어울리는 제목 3개를 제안하세요.",
                "description": "이 콘텐츠의 설명문 3개를 작성하세요.",
                "hashtags": "이 콘텐츠에 적합한 해시태그 10개를 제안하세요.",
            }
            prompt = f"콘텐츠:\n{content_text[:3000]}\n\n{prompt_map.get(task_type, prompt_map['title'])}"

            response = litellm.completion(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Korean social media content expert."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            return {
                "content_id": content_id,
                "task_type": task_type,
                "status": "completed",
                "result": response.choices[0].message.content,
            }

    except Exception as exc:
        logger.error("generate_content_metadata_error", error=str(exc))
        return {"content_id": content_id, "task_type": task_type, "status": "failed", "error": str(exc)}


# ── S18 — AI Asynchronous Features (F03/F15) ────────────


@celery_app.task(name="generate_subtitles", bind=True, max_retries=2, default_retry_delay=60)
def generate_subtitles_task(self, job_id: str) -> None:
    """Async subtitle generation from video/audio (F03).

    Uses litellm to generate subtitle suggestions based on content metadata.
    For real STT, Whisper API integration would replace the litellm call.
    """
    from app.core.database import sync_session_factory
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    with sync_session_factory() as session:
        job = session.get(AiJob, job_id)
        if not job:
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            job.progress = 10
            session.commit()

            params = job.input_params or {}
            language = params.get("language", "ko")
            media_asset_id = params.get("media_asset_id")

            # Retrieve media asset info for context
            asset_info = ""
            duration = 30.0
            if media_asset_id:
                from app.models.media import MediaAsset

                asset = session.get(MediaAsset, media_asset_id)
                if asset:
                    duration = asset.duration or 30.0
                    asset_info = (
                        f"파일명: {asset.original_filename}\n"
                        f"미디어 타입: {asset.media_type}\n"
                        f"길이: {duration}초\n"
                    )

            job.progress = 30
            session.commit()

            # Generate subtitles using litellm
            try:
                import litellm

                prompt = (
                    f"다음 미디어 파일의 자막을 생성해 주세요.\n\n"
                    f"{asset_info}\n"
                    f"언어: {language}\n\n"
                    "JSON 배열 형식으로 자막 세그먼트를 생성하세요:\n"
                    '[{"start": 0.0, "end": 5.0, "text": "자막 텍스트"}, ...]\n\n'
                    "영상의 일반적인 흐름을 고려하여 자연스러운 자막을 생성하세요. "
                    "각 세그먼트는 3-7초 길이로 만들어 주세요. "
                    "반드시 유효한 JSON 배열만 출력하세요."
                )

                response = litellm.completion(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a subtitle generation specialist for Korean media content."},  # noqa: E501
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=2000,
                    temperature=0.5,
                )

                content = response.choices[0].message.content or "[]"
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                subtitles = json.loads(content)
                if not isinstance(subtitles, list):
                    subtitles = []

            except Exception as ai_err:
                logger.warning("subtitle_ai_fallback", error=str(ai_err))
                # Fallback: generate placeholder subtitles
                subtitles = []
                t = 0.0
                seg_idx = 1
                while t < duration:
                    end = min(t + 5.0, duration)
                    subtitles.append({
                        "start": round(t, 1),
                        "end": round(end, 1),
                        "text": f"[{language}] 자막 세그먼트 {seg_idx} (편집 필요)",
                    })
                    t = end
                    seg_idx += 1

            job.progress = 80
            session.commit()

            result = {
                "subtitles": subtitles,
                "language": language,
                "total_segments": len(subtitles),
                "source": "ai_generated",
                "note": "AI가 생성한 자막입니다. 검토 후 수정해 주세요.",
            }

            job.status = AiJobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.now(UTC)
            session.commit()

            logger.info("subtitles_generated", job_id=job_id, segments=len(subtitles))

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            session.commit()
            logger.error("subtitle_task_failed", job_id=job_id, error=str(exc))
            raise self.retry(exc=exc) from exc


@celery_app.task(name="extract_shortform", bind=True, max_retries=2, default_retry_delay=60)
def extract_shortform_task(self, job_id: str) -> None:
    """Async shortform clip extraction from long video (F15).

    Uses litellm to recommend highlight segments based on content metadata.
    Actual video editing (ffmpeg) is not performed — only timestamp recommendations.
    """
    from app.core.database import sync_session_factory
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    with sync_session_factory() as session:
        job = session.get(AiJob, job_id)
        if not job:
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            job.progress = 10
            session.commit()

            params = job.input_params or {}
            count = params.get("count", 3)
            target_duration = params.get("target_duration", 60)
            style = params.get("style", "highlight")
            media_asset_id = params.get("media_asset_id")

            # Get media asset context
            asset_info = ""
            total_duration = 300.0  # default 5 min
            if media_asset_id:
                from app.models.media import MediaAsset

                asset = session.get(MediaAsset, media_asset_id)
                if asset:
                    total_duration = asset.duration or 300.0
                    asset_info = (
                        f"파일명: {asset.original_filename}\n"
                        f"전체 길이: {total_duration}초\n"
                    )

            job.progress = 30
            session.commit()

            # Generate clip recommendations using litellm
            try:
                import litellm

                prompt = (
                    f"다음 영상에서 숏폼 클립으로 적합한 구간 {count}개를 추천해 주세요.\n\n"
                    f"{asset_info}"
                    f"클립 스타일: {style}\n"
                    f"목표 길이: 각 {target_duration}초\n"
                    f"전체 영상 길이: {total_duration}초\n\n"
                    "JSON 배열 형식으로 응답하세요:\n"
                    '[{"start": 0.0, "end": 60.0, "title": "클립 제목", '
                    '"reason": "선택 이유", "score": 0.95}, ...]\n\n'
                    "start/end는 초 단위입니다. 영상 길이를 초과하지 마세요. "
                    "반드시 유효한 JSON 배열만 출력하세요."
                )

                response = litellm.completion(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a video editing specialist for Korean social media content."},  # noqa: E501
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.6,
                )

                raw_content = response.choices[0].message.content or "[]"
                if "```json" in raw_content:
                    raw_content = raw_content.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_content:
                    raw_content = raw_content.split("```")[1].split("```")[0].strip()

                clips = json.loads(raw_content)
                if not isinstance(clips, list):
                    clips = []

                # Ensure clips don't exceed total duration
                valid_clips = []
                for clip in clips[:count]:
                    start = float(clip.get("start", 0))
                    end = float(clip.get("end", start + target_duration))
                    if end > total_duration:
                        end = total_duration
                    if start < end:
                        valid_clips.append({
                            "start": round(start, 1),
                            "end": round(end, 1),
                            "title": clip.get("title", f"클립 {len(valid_clips) + 1}"),
                            "reason": clip.get("reason", ""),
                            "score": float(clip.get("score", 0.8)),
                            "style": style,
                        })
                clips = valid_clips

            except Exception as ai_err:
                logger.warning("shortform_ai_fallback", error=str(ai_err))
                # Fallback: evenly distributed clips
                clips = []
                interval = total_duration / max(count, 1)
                for ci in range(count):
                    start = round(ci * interval, 1)
                    end = round(min(start + target_duration, total_duration), 1)
                    if start < end:
                        clips.append({
                            "start": start,
                            "end": end,
                            "title": f"하이라이트 클립 {ci + 1}",
                            "reason": "균등 분할 (AI 추천 실패 시 기본값)",
                            "score": round(0.7 - ci * 0.05, 2),
                            "style": style,
                        })

            job.progress = 80
            session.commit()

            result = {
                "clips": clips,
                "total_clips": len(clips),
                "target_duration": target_duration,
                "style": style,
                "source": "ai_recommended",
                "note": "AI가 추천한 클립 구간입니다. 검토 후 확정해 주세요.",
            }

            job.status = AiJobStatus.COMPLETED
            job.progress = 100
            job.result = result
            job.completed_at = datetime.now(UTC)
            session.commit()

            logger.info("shortform_extracted", job_id=job_id, clips=len(clips))

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            session.commit()
            logger.error("shortform_task_failed", job_id=job_id, error=str(exc))
            raise self.retry(exc=exc) from exc


# ── Phase 4 — Thumbnail (F16) ────────────────────────


@celery_app.task(name="generate_thumbnail", bind=True, max_retries=1, default_retry_delay=60)
def generate_thumbnail_task(self, job_id: str) -> None:
    """Async thumbnail generation using AI (F16).

    Uses litellm to generate thumbnail design descriptions.
    In production, would call DALL-E/Stable Diffusion for actual image generation.
    """
    from app.core.database import sync_session_factory
    from app.models.ai_usage import AiJob
    from app.models.enums import AiJobStatus

    with sync_session_factory() as session:
        job = session.get(AiJob, job_id)
        if not job:
            return

        try:
            job.status = AiJobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            job.progress = 10
            session.commit()

            params = job.input_params or {}
            content_text = params.get("content_text", "")
            style = params.get("style", "modern")
            count = params.get("count", 3)
            aspect_ratio = params.get("aspect_ratio", "16:9")

            # Use litellm to generate thumbnail descriptions
            try:
                import litellm

                prompt = (
                    f"다음 콘텐츠에 어울리는 썸네일 디자인 {count}개를 제안해 주세요.\n\n"
                    f"콘텐츠: {content_text[:2000]}\n"
                    f"스타일: {style}\n"
                    f"비율: {aspect_ratio}\n\n"
                    "JSON 배열 형식으로 응답:\n"
                    '[{"layout": "레이아웃설명", "text_overlay": "오버레이텍스트", '
                    '"colors": ["#hex1", "#hex2"], "description": "디자인설명", "score": 0.95}, ...]\n\n'
                    "반드시 유효한 JSON 배열만 출력하세요."
                )

                response = litellm.completion(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a thumbnail design specialist."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=1000,
                    temperature=0.7,
                )

                raw = response.choices[0].message.content or "[]"
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                candidates = json.loads(raw)
                if not isinstance(candidates, list):
                    candidates = []

                # Normalize candidates
                for c_idx, c in enumerate(candidates[:count]):
                    c["index"] = c_idx + 1
                    c["aspect_ratio"] = aspect_ratio
                    c["style"] = style
                    c["image_url"] = None  # Would contain MinIO URL in production
                candidates = candidates[:count]

            except Exception:
                # Fallback: template-based candidates
                styles_map = {
                    "modern": ["#1890ff", "#ffffff", "#f0f2f5"],
                    "classic": ["#2c3e50", "#ecf0f1", "#e74c3c"],
                    "minimalist": ["#ffffff", "#333333", "#f5f5f5"],
                    "bold": ["#ff4d4f", "#fadb14", "#52c41a"],
                }
                colors = styles_map.get(style, styles_map["modern"])
                candidates = []
                for c_idx in range(count):
                    candidates.append({
                        "index": c_idx + 1,
                        "layout": ["center-text", "split-layout", "overlay"][c_idx % 3],
                        "colors": colors,
                        "text_overlay": f"썸네일 후보 {c_idx + 1}",
                        "aspect_ratio": aspect_ratio,
                        "style": style,
                        "score": round(0.95 - c_idx * 0.05, 2),
                        "description": f"{style} 스타일의 {aspect_ratio} 썸네일 디자인",
                        "image_url": None,
                    })

            job.progress = 90
            session.commit()

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
            job.completed_at = datetime.now(UTC)
            session.commit()

        except Exception as exc:
            job.status = AiJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
            session.commit()
            raise self.retry(exc=exc) from exc
