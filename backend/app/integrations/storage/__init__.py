"""Storage abstraction layer with pluggable backends.

Usage:
    from app.integrations.storage import get_storage
    storage = get_storage()
    object_key = storage.upload(org_id, file_data, filename, content_type, file_size)

Legacy function aliases (generate_presigned_upload_url, etc.) are preserved
for backward compatibility but delegate to the singleton backend instance.
"""

import functools
from io import BytesIO
from typing import TYPE_CHECKING

import structlog

from app.integrations.storage.base import StorageBackend

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()

# ── Allowed content types (unchanged) ─────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/aac", "audio/ogg", "audio/webm"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/msword"}
ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES | ALLOWED_DOCUMENT_TYPES

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


# ── Singleton factory ─────────────────────────────────────

@functools.lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton.

    Reads ``STORAGE_BACKEND`` from settings:
      - ``"local"``  → LocalStorageBackend (default, development)
      - ``"minio"``  → MinIOStorageBackend (production / S3-compatible)
    """
    from app.core.config import settings

    backend_type = settings.STORAGE_BACKEND.lower()

    if backend_type == "minio":
        from app.integrations.storage.minio_backend import MinIOStorageBackend

        return MinIOStorageBackend(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            secure=settings.MINIO_SECURE,
        )

    # Default: local filesystem
    from app.integrations.storage.local import LocalStorageBackend

    return LocalStorageBackend(root=settings.STORAGE_LOCAL_ROOT)


# ── Legacy function aliases (backward compatibility) ──────
# These delegate to get_storage() so existing code keeps working.


def generate_presigned_upload_url(
    org_id: str,
    filename: str,
    content_type: str,
    expires: int = 3600,
) -> dict:
    return get_storage().presigned_upload_url(org_id, filename, content_type, expires)


def generate_presigned_download_url(object_key: str, expires: int = 3600) -> str:
    return get_storage().presigned_download_url(object_key, expires)


def upload_file_to_storage(
    org_id: str,
    file_data,
    filename: str,
    content_type: str,
    file_size: int,
) -> str:
    return get_storage().upload(org_id, file_data, filename, content_type, file_size)


def get_object_stream(object_key: str) -> tuple:
    return get_storage().download(object_key)


def get_object_stream_range(
    object_key: str, offset: int = 0, length: int = 0
) -> tuple:
    return get_storage().download_range(object_key, offset, length)


def delete_object(object_key: str) -> None:
    get_storage().delete(object_key)


def ensure_bucket() -> None:
    """No-op for local backend; MinIO backend ensures bucket in __init__."""
    storage = get_storage()
    if hasattr(storage, "_ensure_bucket"):
        storage._ensure_bucket()


def get_minio_client():
    """Return the raw MinIO client (MinIO backend only).

    Raises AttributeError if using local backend.
    """
    storage = get_storage()
    if hasattr(storage, "client"):
        return storage.client
    raise AttributeError(
        "get_minio_client() is only available with STORAGE_BACKEND=minio. "
        f"Current backend: {type(storage).__name__}"
    )


# ── Thumbnail / video metadata helpers ───────────────────
# These use the storage backend internally but also need
# ffprobe/Pillow, so they stay as module-level functions.


def _derive_thumb_key(object_key: str) -> str:
    """Derive thumbnail object_key from original object_key.

    Replaces ``orig_`` prefix with ``thumb_`` and changes extension to ``.jpg``.

    Example:
        ``orgs/.../media/orig_aaa111.png`` → ``orgs/.../media/thumb_aaa111.jpg``
    """
    import re

    # Replace the last path segment: orig_<uuid>.<ext> → thumb_<uuid>.jpg
    return re.sub(r"orig_([0-9a-f]+)\.[^/]+$", r"thumb_\1.jpg", object_key)


def generate_thumbnail(
    org_id: str,
    object_key: str,
    size: tuple[int, int] = (200, 200),
    quality: int = 85,
) -> str | None:
    """Generate image thumbnail and save with same UUID as original.

    Original: ``orgs/{org}/media/orig_aaa111.png``
    Thumbnail: ``orgs/{org}/media/thumb_aaa111.jpg``
    """
    try:
        from PIL import Image

        storage = get_storage()

        # Download original
        stream, _ct, _sz = storage.download(object_key)
        original_data = BytesIO(stream.read())
        if hasattr(stream, "close"):
            stream.close()
        if hasattr(stream, "release_conn"):
            stream.release_conn()

        # Resize
        img = Image.open(original_data)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        thumb_buffer = BytesIO()
        img.save(thumb_buffer, format="JPEG", quality=quality)
        thumb_buffer.seek(0)
        thumb_size = thumb_buffer.getbuffer().nbytes

        # Save thumbnail with derived key (same UUID, thumb_ prefix)
        thumb_key = _derive_thumb_key(object_key)
        storage.save_direct(thumb_key, thumb_buffer, "image/jpeg", thumb_size)

        logger.info(
            "thumbnail_generated",
            original_key=object_key,
            thumb_key=thumb_key,
            thumb_size=thumb_size,
        )
        return thumb_key

    except Exception as e:
        logger.error("thumbnail_generation_failed", object_key=object_key, error=str(e))
        return None


def get_video_metadata(object_key: str) -> dict | None:
    """Extract video metadata (duration, width, height) using ffprobe."""
    import json as _json
    import os
    import subprocess
    import tempfile

    try:
        storage = get_storage()
        stream, _ct, _sz = storage.download(object_key)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
            while True:
                chunk = stream.read(32 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        if hasattr(stream, "close"):
            stream.close()
        if hasattr(stream, "release_conn"):
            stream.release_conn()

        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", tmp_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)  # noqa: S603
        os.unlink(tmp_path)

        if result.returncode != 0:
            logger.warning("ffprobe_failed", object_key=object_key, stderr=result.stderr[:200])
            return None

        probe = _json.loads(result.stdout)
        duration = float(probe.get("format", {}).get("duration", 0))

        width = height = None
        for s in probe.get("streams", []):
            if s.get("codec_type") == "video":
                width = s.get("width")
                height = s.get("height")
                break

        return {"duration": duration, "width": width, "height": height}

    except FileNotFoundError:
        logger.warning("ffprobe_not_installed", object_key=object_key)
        return None
    except Exception as e:
        logger.error("video_metadata_extraction_failed", object_key=object_key, error=str(e))
        return None


def generate_video_thumbnail(
    org_id: str,
    object_key: str,
    time_offset: float = 3.0,
    size: tuple[int, int] = (320, 180),
) -> str | None:
    """Extract a frame from video and create a thumbnail."""
    import os
    import subprocess
    import tempfile

    try:
        from PIL import Image

        storage = get_storage()

        # Download video to temp file
        stream, _ct, _sz = storage.download(object_key)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            tmp_video_path = tmp_video.name
            while True:
                chunk = stream.read(32 * 1024)
                if not chunk:
                    break
                tmp_video.write(chunk)
        if hasattr(stream, "close"):
            stream.close()
        if hasattr(stream, "release_conn"):
            stream.release_conn()

        # Extract frame using ffmpeg
        tmp_frame_path = tmp_video_path + ".jpg"
        cmd = [
            "ffmpeg", "-y", "-ss", str(time_offset),
            "-i", tmp_video_path,
            "-frames:v", "1", "-q:v", "2",
            tmp_frame_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)  # noqa: S603
        os.unlink(tmp_video_path)

        if result.returncode != 0 or not os.path.exists(tmp_frame_path):
            logger.warning("ffmpeg_frame_extraction_failed", object_key=object_key)
            return None

        # Resize with Pillow
        img = Image.open(tmp_frame_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        thumb_buffer = BytesIO()
        img.save(thumb_buffer, format="JPEG", quality=85)
        thumb_buffer.seek(0)
        thumb_size = thumb_buffer.getbuffer().nbytes
        os.unlink(tmp_frame_path)

        # Save thumbnail with derived key (same UUID, thumb_ prefix)
        thumb_key = _derive_thumb_key(object_key)
        storage.save_direct(thumb_key, thumb_buffer, "image/jpeg", thumb_size)

        logger.info(
            "video_thumbnail_generated",
            original_key=object_key,
            thumb_key=thumb_key,
            thumb_size=thumb_size,
        )
        return thumb_key

    except FileNotFoundError:
        logger.warning("ffmpeg_not_installed", object_key=object_key)
        return None
    except Exception as e:
        logger.error("video_thumbnail_generation_failed", object_key=object_key, error=str(e))
        return None


__all__ = [
    "ALLOWED_AUDIO_TYPES",
    "ALLOWED_CONTENT_TYPES",
    "ALLOWED_DOCUMENT_TYPES",
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_VIDEO_TYPES",
    "MAX_FILE_SIZE",
    "StorageBackend",
    "delete_object",
    "ensure_bucket",
    "generate_presigned_download_url",
    "generate_presigned_upload_url",
    "generate_thumbnail",
    "generate_video_thumbnail",
    "get_minio_client",
    "get_object_stream",
    "get_object_stream_range",
    "get_storage",
    "get_video_metadata",
    "upload_file_to_storage",
]
