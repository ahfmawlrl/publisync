"""MinIO S3-compatible storage client for media file management."""

import uuid
from datetime import timedelta
from io import BytesIO

import structlog
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = structlog.get_logger()

# ── Allowed content types ─────────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/aac", "audio/ogg", "audio/webm"}
ALLOWED_DOCUMENT_TYPES = {"application/pdf", "application/msword"}
ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES | ALLOWED_DOCUMENT_TYPES

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def _get_client() -> Minio:
    """Create a new MinIO client instance."""
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def _rewrite_to_proxy_url(url: str) -> str:
    """Rewrite a MinIO presigned URL to use the /storage proxy path.

    The browser cannot directly reach MinIO (CORS / Docker networking).
    Both Vite dev-server and Nginx production proxy route ``/storage/…``
    to the MinIO endpoint, stripping the ``/storage`` prefix.

    Example::

        http://localhost:9000/publisync-media/orgs/.../file.mp4?X-Amz-…
        → /storage/publisync-media/orgs/.../file.mp4?X-Amz-…

    The ``changeOrigin`` option in the proxy ensures MinIO receives
    the original ``Host`` header, so the presigned signature stays valid.
    """
    scheme = "https" if settings.MINIO_SECURE else "http"
    minio_origin = f"{scheme}://{settings.MINIO_ENDPOINT}"
    if url.startswith(minio_origin):
        rewritten = url.replace(minio_origin, "/storage", 1)
        logger.debug(
            "presigned_url_rewritten",
            original_prefix=url[:60],
            rewritten_prefix=rewritten[:60],
        )
        return rewritten
    # URL이 예상 origin으로 시작하지 않으면 경고 로그
    logger.warning(
        "presigned_url_rewrite_skipped",
        url_prefix=url[:60],
        expected_origin=minio_origin,
    )
    return url


def ensure_bucket() -> None:
    """Create the default bucket if it doesn't exist."""
    client = _get_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
        logger.info("minio_bucket_created", bucket=settings.MINIO_BUCKET)


def generate_presigned_upload_url(
    org_id: str,
    filename: str,
    content_type: str,
    expires: int = 3600,
) -> dict:
    """Generate a presigned PUT URL for direct client-side upload.

    Returns:
        dict with `upload_url`, `object_key`, and `public_url`.
    """
    client = _get_client()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    object_key = f"orgs/{org_id}/media/{unique_name}"

    raw_upload_url = client.presigned_put_object(
        settings.MINIO_BUCKET,
        object_key,
        expires=timedelta(seconds=expires),
    )

    # Rewrite URLs through the /storage proxy so the browser can reach MinIO.
    upload_url = _rewrite_to_proxy_url(raw_upload_url)
    public_url = f"/storage/{settings.MINIO_BUCKET}/{object_key}"

    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "public_url": public_url,
        "content_type": content_type,
        "filename": filename,
    }


def generate_presigned_download_url(object_key: str, expires: int = 3600) -> str:
    """Generate a presigned GET URL for downloading a private object.

    The returned URL goes through the ``/storage`` reverse-proxy so the
    browser can fetch the file without CORS / Docker networking issues.
    """
    client = _get_client()
    raw_url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_key,
        expires=timedelta(seconds=expires),
    )
    return _rewrite_to_proxy_url(raw_url)


def upload_file_to_storage(
    org_id: str,
    file_data,
    filename: str,
    content_type: str,
    file_size: int,
) -> str:
    """Upload a file to MinIO directly from the backend.

    This is the server-side alternative to presigned URL uploads.
    The file data is streamed from the backend to MinIO without
    buffering the entire file in memory.

    Args:
        org_id: Organization ID for path partitioning.
        file_data: File-like object (e.g., ``UploadFile.file``).
        filename: Original filename (used for extension).
        content_type: MIME type of the file.
        file_size: Size in bytes.

    Returns:
        The MinIO object key where the file was stored.
    """
    client = _get_client()
    ensure_bucket()

    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    object_key = f"orgs/{org_id}/media/{unique_name}"

    client.put_object(
        settings.MINIO_BUCKET,
        object_key,
        data=file_data,
        length=file_size,
        content_type=content_type,
    )

    logger.info(
        "file_uploaded_to_storage",
        object_key=object_key,
        file_size=file_size,
        content_type=content_type,
    )
    return object_key


def get_object_stream(object_key: str) -> tuple:
    """Get a streaming response for a MinIO object.

    Returns:
        Tuple of (data_stream, content_type, content_length) where
        data_stream is an iterable that yields chunks.  The caller
        MUST close the returned stream (``response.close();
        response.release_conn()``) after consumption.
    """
    client = _get_client()
    stat = client.stat_object(settings.MINIO_BUCKET, object_key)
    response = client.get_object(settings.MINIO_BUCKET, object_key)
    return response, stat.content_type or "application/octet-stream", stat.size


def get_object_stream_range(
    object_key: str, offset: int = 0, length: int = 0
) -> tuple:
    """Get a partial streaming response for a MinIO object (HTTP Range).

    Args:
        object_key: The MinIO object key.
        offset: Start byte position (inclusive).
        length: Number of bytes to read.  ``0`` means read to end-of-file.

    Returns:
        Tuple of (data_stream, content_type, total_size) where
        ``total_size`` is the *full* object size (for Content-Range header).
        The caller MUST close the returned stream.
    """
    client = _get_client()
    stat = client.stat_object(settings.MINIO_BUCKET, object_key)
    total_size = stat.size
    content_type = stat.content_type or "application/octet-stream"

    response = client.get_object(
        settings.MINIO_BUCKET,
        object_key,
        offset=offset,
        length=length or 0,
    )
    return response, content_type, total_size


def get_video_metadata(object_key: str) -> dict | None:
    """Extract video metadata (duration, width, height) using ffprobe.

    Returns:
        dict with duration, width, height, or None on failure.
    """
    import json as _json
    import os
    import subprocess
    import tempfile

    try:
        client = _get_client()

        # Download video to temp file (ffprobe needs file access)
        response = client.get_object(settings.MINIO_BUCKET, object_key)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
            for chunk in response.stream(32 * 1024):
                tmp.write(chunk)
        response.close()
        response.release_conn()

        # Run ffprobe
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
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width")
                height = stream.get("height")
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
    """Extract a frame from video at time_offset and create a thumbnail.

    Uses ffmpeg to extract a frame, then Pillow to resize.

    Args:
        org_id: Organization ID for storage path.
        object_key: MinIO video object key.
        time_offset: Time in seconds to extract frame at. Default 3s.
        size: Thumbnail size (width, height). Default 320x180.

    Returns:
        Thumbnail object key, or None on failure.
    """
    import os
    import subprocess
    import tempfile

    try:
        from PIL import Image

        client = _get_client()

        # Download video to temp file
        response = client.get_object(settings.MINIO_BUCKET, object_key)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_video:
            tmp_video_path = tmp_video.name
            for chunk in response.stream(32 * 1024):
                tmp_video.write(chunk)
        response.close()
        response.release_conn()

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

        # Upload thumbnail to MinIO
        thumb_key = f"orgs/{org_id}/thumbnails/{uuid.uuid4().hex}.jpg"
        client.put_object(
            settings.MINIO_BUCKET,
            thumb_key,
            data=thumb_buffer,
            length=thumb_size,
            content_type="image/jpeg",
        )

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


def delete_object(object_key: str) -> None:
    """Delete an object from the bucket."""
    client = _get_client()
    try:
        client.remove_object(settings.MINIO_BUCKET, object_key)
        logger.info("minio_object_deleted", key=object_key)
    except S3Error as e:
        logger.error("minio_delete_failed", key=object_key, error=str(e))
        raise


def generate_thumbnail(
    org_id: str,
    object_key: str,
    size: tuple[int, int] = (200, 200),
    quality: int = 85,
) -> str | None:
    """원본 이미지에서 썸네일을 생성하여 MinIO에 업로드.

    Args:
        org_id: 기관 ID (저장 경로에 사용).
        object_key: MinIO 원본 이미지 object key.
        size: 썸네일 최대 크기 (width, height). 기본 200x200.
        quality: JPEG 압축 품질 (1-95). 기본 85.

    Returns:
        썸네일 object key 문자열, 실패 시 None.
    """
    try:
        from PIL import Image

        client = _get_client()

        # 1. MinIO에서 원본 이미지 다운로드
        response = client.get_object(settings.MINIO_BUCKET, object_key)
        original_data = BytesIO(response.read())
        response.close()
        response.release_conn()

        # 2. Pillow로 열고 썸네일 리사이즈
        img = Image.open(original_data)
        img.thumbnail(size, Image.Resampling.LANCZOS)

        # 3. RGBA → RGB 변환 (JPEG 저장용)
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        # 4. BytesIO에 JPEG로 저장
        thumb_buffer = BytesIO()
        img.save(thumb_buffer, format="JPEG", quality=quality)
        thumb_buffer.seek(0)
        thumb_size = thumb_buffer.getbuffer().nbytes

        # 5. MinIO에 썸네일 업로드
        thumb_key = f"orgs/{org_id}/thumbnails/{uuid.uuid4().hex}.jpg"
        client.put_object(
            settings.MINIO_BUCKET,
            thumb_key,
            data=thumb_buffer,
            length=thumb_size,
            content_type="image/jpeg",
        )

        logger.info(
            "thumbnail_generated",
            original_key=object_key,
            thumb_key=thumb_key,
            thumb_size=thumb_size,
        )
        return thumb_key

    except Exception as e:
        logger.error(
            "thumbnail_generation_failed",
            object_key=object_key,
            error=str(e),
        )
        return None
