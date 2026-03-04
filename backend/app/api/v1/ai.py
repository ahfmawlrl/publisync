"""AI API — 14 endpoints (S11 F02 + S17 F05/F17/F21 + S18 F03/F15 + Phase 3 F20 + Phase 4 F16/F22).

POST /ai/generate-title        (AM, AO)
POST /ai/generate-description   (AM, AO)
POST /ai/generate-hashtags      (AM, AO)
POST /ai/generate-reply         (AM, AO) — S17
POST /ai/improve-template       (AM, AO) — S17
POST /ai/tone-transform         (AM, AO) — S17
POST /ai/content-review         (AM, AO) — S17
POST /ai/suggest-effects        (AM, AO) — S17
POST /ai/generate-subtitles     (AM, AO) — S18
POST /ai/extract-shortform      (AM, AO) — S18
GET  /ai/jobs/{job_id}          (AM, AO) — S18
POST /ai/optimal-time           (AM, AO) — Phase 3
POST /ai/generate-thumbnail     (AM, AO) — Phase 4
POST /ai/translate              (AM, AO) — Phase 4
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.deps import WorkspaceContext, get_workspace_context, require_roles
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.ai_usage_repository import AiUsageRepository
from app.schemas.ai import (
    AiContentReviewRequest,
    AiContentReviewResponse,
    AiGenerateRequest,
    AiGenerateResponse,
    AiImproveTemplateRequest,
    AiOptimalTimeRequest,
    AiReplyRequest,
    AiShortformRequest,
    AiSubtitleRequest,
    AiSuggestEffectsRequest,
    AiThumbnailRequest,
    AiToneTransformRequest,
    AiTranslateRequest,
    AiTranslateResponse,
)
from app.schemas.common import ApiResponse
from app.services.ai_service import AiService

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db_session)) -> AiService:
    return AiService(AiUsageRepository(db))


# ── POST /ai/generate-title ────────────────────────────────
@router.post("/generate-title", response_model=ApiResponse[AiGenerateResponse])
async def generate_title(
    body: AiGenerateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.generate_title(
        content_text=body.content_text,
        platform=body.platform,
        language=body.language,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/generate-description ──────────────────────────
@router.post("/generate-description", response_model=ApiResponse[AiGenerateResponse])
async def generate_description(
    body: AiGenerateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.generate_description(
        content_text=body.content_text,
        platform=body.platform,
        language=body.language,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/generate-hashtags ─────────────────────────────
@router.post("/generate-hashtags", response_model=ApiResponse[AiGenerateResponse])
async def generate_hashtags(
    body: AiGenerateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.generate_hashtags(
        content_text=body.content_text,
        platform=body.platform,
        language=body.language,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── S17 — AI Synchronous Features (F05/F17/F21) ──────────


# ── POST /ai/generate-reply ─────────────────────────────
@router.post("/generate-reply", response_model=ApiResponse[AiGenerateResponse])
async def generate_reply(
    body: AiReplyRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.generate_reply(
        comment_text=body.comment_text,
        content_context=body.content_context,
        tone=body.tone,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/improve-template ───────────────────────────
@router.post("/improve-template", response_model=ApiResponse[AiGenerateResponse])
async def improve_template(
    body: AiImproveTemplateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.improve_template(
        template_text=body.template_text,
        purpose=body.purpose,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/tone-transform ────────────────────────────
@router.post("/tone-transform", response_model=ApiResponse[AiGenerateResponse])
async def tone_transform(
    body: AiToneTransformRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.tone_transform(
        content_text=body.content_text,
        target_platform=body.target_platform,
        target_tone=body.target_tone,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/content-review ────────────────────────────
@router.post("/content-review", response_model=ApiResponse[AiContentReviewResponse])
async def content_review(
    body: AiContentReviewRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.content_review(
        content_text=body.content_text,
        check_spelling=body.check_spelling,
        check_sensitivity=body.check_sensitivity,
        check_bias=body.check_bias,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── POST /ai/suggest-effects ───────────────────────────
@router.post("/suggest-effects", response_model=ApiResponse[AiGenerateResponse])
async def suggest_effects(
    body: AiSuggestEffectsRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.suggest_effects(
        content_text=body.content_text,
        content_type=body.content_type,
        count=body.count,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── S18 — AI Asynchronous Features (F03/F15) ────────────


# ── POST /ai/generate-subtitles ─────────────────────────
@router.post("/generate-subtitles", status_code=status.HTTP_202_ACCEPTED)
async def generate_subtitles(
    body: AiSubtitleRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    """Create async subtitle generation job (202 Accepted)."""
    from uuid import UUID as PyUUID

    job = await service.create_subtitle_job(
        org_id=workspace.org_id,
        user_id=workspace.user.id,
        media_asset_id=PyUUID(body.media_asset_id),
        language=body.language,
        include_timestamps=body.include_timestamps,
    )
    return {
        "success": True,
        "data": {
            "job_id": str(job.id),
            "job_type": "SUBTITLE",
            "status": "PENDING",
            "message": "자막 생성 작업이 대기열에 추가되었습니다.",
        },
    }


# ── POST /ai/extract-shortform ──────────────────────────
@router.post("/extract-shortform", status_code=status.HTTP_202_ACCEPTED)
async def extract_shortform(
    body: AiShortformRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    """Create async shortform extraction job (202 Accepted)."""
    from uuid import UUID as PyUUID

    job = await service.create_shortform_job(
        org_id=workspace.org_id,
        user_id=workspace.user.id,
        media_asset_id=PyUUID(body.media_asset_id),
        target_duration=body.target_duration,
        count=body.count,
        style=body.style,
    )
    return {
        "success": True,
        "data": {
            "job_id": str(job.id),
            "job_type": "SHORTFORM",
            "status": "PENDING",
            "message": "숏폼 추출 작업이 대기열에 추가되었습니다.",
        },
    }


# ── GET /ai/jobs/{job_id} ───────────────────────────────
@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    """Poll async job status."""
    job = await service.get_job_status(job_id=job_id, org_id=workspace.org_id)
    if not job:
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": "작업을 찾을 수 없습니다.",
                },
            },
        )
    return {
        "success": True,
        "data": {
            "job_id": str(job.id),
            "job_type": job.job_type.value if hasattr(job.job_type, "value") else str(job.job_type),
            "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            "progress": job.progress,
            "result": job.result,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "created_at": job.created_at.isoformat()
            if hasattr(job.created_at, "isoformat")
            else str(job.created_at),
        },
    }


# ── Phase 3 — Optimal Time (F20) ─────────────────────


@router.post("/optimal-time")
async def recommend_optimal_time(
    body: AiOptimalTimeRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    result = await service.recommend_optimal_time(
        content_text=body.content_text,
        platforms=body.platforms,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}


# ── Phase 4 — Thumbnail (F16) + Translation (F22) ────


@router.post("/generate-thumbnail", status_code=status.HTTP_202_ACCEPTED)
async def generate_thumbnail(
    body: AiThumbnailRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    """Create async thumbnail generation job (202 Accepted)."""
    job = await service.create_thumbnail_job(
        org_id=workspace.org_id,
        user_id=workspace.user.id,
        content_text=body.content_text,
        style=body.style,
        count=body.count,
        aspect_ratio=body.aspect_ratio,
    )
    return {
        "success": True,
        "data": {
            "job_id": str(job.id),
            "job_type": "THUMBNAIL",
            "status": "PENDING",
            "message": "썸네일 생성 작업이 대기열에 추가되었습니다.",
        },
    }


@router.post("/translate", response_model=ApiResponse[AiTranslateResponse])
async def translate_content(
    body: AiTranslateRequest,
    workspace: WorkspaceContext = Depends(get_workspace_context),
    _user: User = Depends(require_roles(UserRole.AGENCY_MANAGER, UserRole.AGENCY_OPERATOR)),
    service: AiService = Depends(_get_service),
) -> dict:
    """Translate content to target language (synchronous, < 10s)."""
    result = await service.translate(
        content_text=body.content_text,
        target_language=body.target_language,
        source_language=body.source_language,
        preserve_formatting=body.preserve_formatting,
        org_id=workspace.org_id,
        user_id=workspace.user.id,
    )
    return {"success": True, "data": result}
