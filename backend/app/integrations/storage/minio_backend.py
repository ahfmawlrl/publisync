"""MinIO / S3-compatible storage backend."""

import uuid
from datetime import timedelta
from typing import BinaryIO

import structlog
import urllib3
from minio import Minio
from minio.error import S3Error

from app.integrations.storage.base import StorageBackend

logger = structlog.get_logger()

# Short timeout so presigned-upload fails fast when MinIO is down
_MINIO_HTTP = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=3.0, read=5.0),
    retries=urllib3.Retry(total=0),
)


class MinIOStorageBackend(StorageBackend):
    """S3-compatible storage using MinIO client.

    Also works with AWS S3 or any S3-compatible service.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        self._endpoint = endpoint
        self._bucket = bucket
        self._secure = secure
        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            http_client=_MINIO_HTTP,
        )
        self._ensure_bucket()
        logger.info(
            "minio_storage_initialized",
            endpoint=endpoint,
            bucket=bucket,
        )

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("minio_bucket_created", bucket=self._bucket)

    def _generate_key(self, org_id: str, filename: str, prefix: str = "media") -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        return f"orgs/{org_id}/{prefix}/{unique_name}"

    def _rewrite_to_proxy_url(self, url: str) -> str:
        """Rewrite MinIO presigned URL to use the /storage proxy path.

        The browser cannot reach MinIO directly (CORS / Docker networking).
        Both Vite dev-server and Nginx route ``/storage/…`` to MinIO.
        """
        scheme = "https" if self._secure else "http"
        minio_origin = f"{scheme}://{self._endpoint}"
        if url.startswith(minio_origin):
            rewritten = url.replace(minio_origin, "/storage", 1)
            logger.debug(
                "presigned_url_rewritten",
                original_prefix=url[:60],
                rewritten_prefix=rewritten[:60],
            )
            return rewritten
        logger.warning(
            "presigned_url_rewrite_skipped",
            url_prefix=url[:60],
            expected_origin=minio_origin,
        )
        return url

    # ── Core operations ──────────────────────────────────────

    def upload(
        self,
        org_id: str,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        object_key = self._generate_key(org_id, filename)
        self._client.put_object(
            self._bucket,
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

    def download(self, object_key: str) -> tuple[BinaryIO, str, int]:
        stat = self._client.stat_object(self._bucket, object_key)
        response = self._client.get_object(self._bucket, object_key)
        return response, stat.content_type or "application/octet-stream", stat.size

    def download_range(
        self, object_key: str, offset: int = 0, length: int = 0
    ) -> tuple[BinaryIO, str, int]:
        stat = self._client.stat_object(self._bucket, object_key)
        total_size = stat.size
        content_type = stat.content_type or "application/octet-stream"
        response = self._client.get_object(
            self._bucket,
            object_key,
            offset=offset,
            length=length or 0,
        )
        return response, content_type, total_size

    def delete(self, object_key: str) -> None:
        try:
            self._client.remove_object(self._bucket, object_key)
            logger.info("minio_object_deleted", key=object_key)
        except S3Error as e:
            logger.error("minio_delete_failed", key=object_key, error=str(e))
            raise

    # ── Presigned URLs ────────────────────────────────────────

    def presigned_upload_url(
        self,
        org_id: str,
        filename: str,
        content_type: str,
        expires: int = 3600,
    ) -> dict:
        object_key = self._generate_key(org_id, filename)
        raw_upload_url = self._client.presigned_put_object(
            self._bucket,
            object_key,
            expires=timedelta(seconds=expires),
        )
        upload_url = self._rewrite_to_proxy_url(raw_upload_url)
        return {
            "upload_url": upload_url,
            "object_key": object_key,
            "public_url": self.public_url(object_key),
            "content_type": content_type,
            "filename": filename,
        }

    def presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        raw_url = self._client.presigned_get_object(
            self._bucket,
            object_key,
            expires=timedelta(seconds=expires),
        )
        return self._rewrite_to_proxy_url(raw_url)

    def public_url(self, object_key: str) -> str:
        return f"/storage/{self._bucket}/{object_key}"

    # ── Direct client access (for thumbnail/video operations) ─

    @property
    def client(self) -> Minio:
        """Expose raw Minio client for advanced operations (thumbnails, ffprobe)."""
        return self._client

    @property
    def bucket(self) -> str:
        return self._bucket
