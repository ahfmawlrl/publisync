"""Pydantic schemas for Media Library endpoints — Phase 2 (F11)."""

from pydantic import BaseModel, Field

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class MediaAssetResponse(BaseModel):
    id: str
    organization_id: str
    filename: str
    original_filename: str
    mime_type: str
    media_type: str
    object_key: str
    file_size: int
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = []
    metadata: dict | None = None
    folder_id: str | None = None
    thumbnail_url: str | None = None
    version: int = 1
    created_by: str
    created_at: str
    updated_at: str


class MediaAssetListItem(BaseModel):
    id: str
    organization_id: str
    filename: str
    original_filename: str
    mime_type: str
    media_type: str
    object_key: str
    file_size: int
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = []
    folder_id: str | None = None
    thumbnail_url: str | None = None
    version: int = 1
    created_by: str
    created_at: str
    updated_at: str


class MediaUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    original_filename: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., min_length=1, max_length=100)
    object_key: str = Field(..., min_length=1, max_length=1024)
    file_size: int = Field(..., gt=0, le=MAX_FILE_SIZE)
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    tags: list[str] = []
    metadata: dict | None = None
    folder_id: str | None = None


class MediaUpdateRequest(BaseModel):
    filename: str | None = None
    tags: list[str] | None = None
    folder_id: str | None = None


class MediaFolderResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    parent_id: str | None = None
    created_at: str


class MediaFolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: str | None = None


class PresignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0, le=MAX_FILE_SIZE)


class SubtitleSegment(BaseModel):
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    text: str = Field(..., min_length=1, max_length=2000)


class SubtitleUpdateRequest(BaseModel):
    subtitles: list[SubtitleSegment] = Field(..., min_length=1, max_length=500)
    language: str = Field(default="ko", min_length=2, max_length=10)
