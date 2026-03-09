"""Pydantic schemas for AI endpoints — S11 (F02)."""

from pydantic import BaseModel, Field


class AiGenerateRequest(BaseModel):
    """Request body for AI text generation endpoints."""

    content_text: str = Field(..., min_length=1, max_length=5000, description="Source content text")
    platform: str | None = Field(None, description="Target platform (YOUTUBE, INSTAGRAM, etc.)")
    language: str = Field("ko", description="Output language code")
    count: int = Field(3, ge=1, le=10, description="Number of suggestions to generate")


class AiSuggestion(BaseModel):
    """Single AI-generated suggestion with confidence score."""

    content: str
    score: float = Field(..., ge=0.0, le=1.0)


class AiGenerateResponse(BaseModel):
    """Standard Human-in-the-Loop AI response with suggestions."""

    isAiGenerated: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    fallbackAvailable: bool = True
    model: str
    suggestions: list[AiSuggestion] = []
    usage: dict = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
    )
    processing_time_ms: int = 0
    error: str | None = None


class AiTaskTypeUsage(BaseModel):
    """Per-task-type usage breakdown."""

    task_type: str
    request_count: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0


class AiUsageResponse(BaseModel):
    """Aggregated AI usage statistics for an organization."""

    organization_id: str
    total_requests: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    by_task_type: list[AiTaskTypeUsage] = []


# ── S17 — AI Synchronous Features (F05/F17/F21) ──────────


class AiReplyRequest(BaseModel):
    """Request for AI reply generation (F05)."""

    comment_text: str = Field(..., min_length=1, max_length=2000, description="Original comment text")
    content_context: str | None = Field(None, max_length=3000, description="Related content context")
    tone: str = Field("formal", description="Reply tone: formal, friendly, empathetic")
    count: int = Field(2, ge=1, le=5)


class AiToneTransformRequest(BaseModel):
    """Request for tone transformation (F17)."""

    content_text: str = Field(..., min_length=1, max_length=5000)
    target_platform: str = Field(
        ..., description="Target platform: YOUTUBE, INSTAGRAM, FACEBOOK, X, NAVER_BLOG"
    )
    target_tone: str = Field("formal", description="Target tone: formal, casual, friendly, professional")
    count: int = Field(1, ge=1, le=3)


class AiContentReviewRequest(BaseModel):
    """Request for content review/audit (F21)."""

    content_text: str = Field(..., min_length=1, max_length=10000)
    check_spelling: bool = Field(True)
    check_sensitivity: bool = Field(True)
    check_bias: bool = Field(True)


class AiContentReviewIssue(BaseModel):
    """Single review issue found."""

    issue: str
    severity: str  # HIGH, MEDIUM, LOW
    location: str | None = None
    suggestion: str
    score: float = Field(0.0, ge=0.0, le=1.0)


class AiContentReviewResponse(BaseModel):
    """Content review response with issues list."""

    isAiGenerated: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    fallbackAvailable: bool = True
    model: str
    issues: list[AiContentReviewIssue] = []
    summary: str = ""
    usage: dict = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
    )
    processing_time_ms: int = 0
    error: str | None = None


class AiSuggestEffectsRequest(BaseModel):
    """Request for effects/emoji suggestion (F03)."""

    content_text: str = Field(..., min_length=1, max_length=5000)
    content_type: str = Field(
        "general", description="Content type: general, celebration, announcement, educational"
    )
    count: int = Field(5, ge=1, le=10)


class AiImproveTemplateRequest(BaseModel):
    """Request for template improvement (F05)."""

    template_text: str = Field(..., min_length=1, max_length=2000)
    purpose: str = Field("reply", description="Template purpose: reply, announcement, greeting")
    count: int = Field(2, ge=1, le=5)


# ── S18 — AI Asynchronous Features (F03/F15) ────────────


class AiJobCreateResponse(BaseModel):
    """Response for async job creation (202 Accepted)."""

    job_id: str
    job_type: str
    status: str = "PENDING"
    message: str = "작업이 대기열에 추가되었습니다."


class AiJobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    job_type: str
    status: str
    progress: int = 0  # 0-100
    result: dict | None = None
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str


class AiSubtitleRequest(BaseModel):
    """Request for AI subtitle generation (F03)."""

    media_asset_id: str = Field(..., description="Media asset ID (video/audio)")
    language: str = Field("ko", description="Target language code")
    include_timestamps: bool = Field(True)


class AiShortformRequest(BaseModel):
    """Request for AI shortform extraction (F15)."""

    media_asset_id: str = Field(..., description="Source video media asset ID")
    target_duration: int = Field(60, ge=15, le=180, description="Target duration in seconds")
    count: int = Field(3, ge=1, le=5, description="Number of shortform candidates")
    style: str = Field("highlight", description="Style: highlight, summary, teaser")


class ShortformClipSegment(BaseModel):
    """Single shortform clip segment."""

    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    title: str = Field("", max_length=200)
    reason: str = Field("", max_length=500)


class ShortformConfirmRequest(BaseModel):
    """Request to confirm selected shortform clips (F15)."""

    job_id: str = Field(..., description="Shortform extraction job ID")
    selected_clips: list[ShortformClipSegment] = Field(
        ..., min_length=1, max_length=10, description="Selected clip segments to confirm"
    )


# ── Phase 3 — Optimal Time (F20) ─────────────────────


class AiOptimalTimeRequest(BaseModel):
    """Request for optimal posting time recommendation (F20)."""

    content_text: str = Field(..., min_length=1, max_length=5000, description="Content text to analyze")
    platforms: list[str] = Field(default_factory=list, description="Target platforms")


class AiOptimalTimeSlot(BaseModel):
    day_of_week: str
    time_range: str
    reason: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class AiOptimalTimeResponse(BaseModel):
    """Response for optimal time recommendation."""

    isAiGenerated: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    fallbackAvailable: bool = True
    model: str
    optimal_times: list[AiOptimalTimeSlot] = []
    usage: dict = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
    )
    processing_time_ms: int = 0
    error: str | None = None


# ── Phase 4 — Thumbnail (F16) + Translation (F22) ────


class AiThumbnailRequest(BaseModel):
    """Request for AI thumbnail generation (F16, async)."""

    content_text: str = Field(..., min_length=1, max_length=5000, description="Content to generate thumbnail for")
    style: str = Field("modern", description="Thumbnail style: modern, classic, minimalist, bold")
    count: int = Field(3, ge=1, le=5, description="Number of thumbnail candidates")
    aspect_ratio: str = Field("16:9", description="Aspect ratio: 16:9, 1:1, 4:3, 9:16")


class AiTranslateRequest(BaseModel):
    """Request for AI translation (F22, synchronous)."""

    content_text: str = Field(..., min_length=1, max_length=10000, description="Content to translate")
    target_language: str = Field(..., description="Target language: en, zh, ja, vi")
    source_language: str = Field("ko", description="Source language code")
    preserve_formatting: bool = Field(True, description="Preserve original formatting")


class AiTranslateResponse(BaseModel):
    """Response for AI translation."""

    isAiGenerated: bool = True
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    fallbackAvailable: bool = True
    model: str
    translated_text: str = ""
    target_language: str = ""
    source_language: str = "ko"
    notes: str = ""
    usage: dict = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
        }
    )
    processing_time_ms: int = 0
    error: str | None = None
