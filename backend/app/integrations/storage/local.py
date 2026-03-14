"""Local filesystem storage backend for development."""

import mimetypes
import shutil
import uuid
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import structlog

from app.integrations.storage.base import StorageBackend

logger = structlog.get_logger()


class LocalStorageBackend(StorageBackend):
    """Store files on the local filesystem under a configurable root directory.

    Intended for development only. Files are served via a dedicated FastAPI
    endpoint (``GET /api/v1/storage/files/{key:path}``).
    """

    def __init__(self, root: str = "./uploads") -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        logger.info("local_storage_initialized", root=str(self._root))

    def _full_path(self, object_key: str) -> Path:
        # Prevent path traversal
        safe = Path(object_key).as_posix().lstrip("/")
        return self._root / safe

    def _generate_key(self, org_id: str, filename: str, prefix: str = "media") -> str:
        ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
        unique_name = f"orig_{uuid.uuid4().hex}.{ext}" if ext else f"orig_{uuid.uuid4().hex}"
        return f"orgs/{org_id}/{prefix}/{unique_name}"

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
        dest = self._full_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            shutil.copyfileobj(file_data, f)

        logger.info(
            "local_file_uploaded",
            object_key=object_key,
            file_size=file_size,
            content_type=content_type,
        )
        return object_key

    def download(self, object_key: str) -> tuple[BinaryIO, str, int]:
        path = self._full_path(object_key)
        if not path.is_file():
            raise FileNotFoundError(f"Object not found: {object_key}")

        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        file_size = path.stat().st_size
        stream = open(path, "rb")
        return stream, content_type, file_size

    def download_range(
        self, object_key: str, offset: int = 0, length: int = 0
    ) -> tuple[BinaryIO, str, int]:
        path = self._full_path(object_key)
        if not path.is_file():
            raise FileNotFoundError(f"Object not found: {object_key}")

        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        total_size = path.stat().st_size

        f = open(path, "rb")
        if offset:
            f.seek(offset)
        if length:
            data = f.read(length)
            f.close()
            return BytesIO(data), content_type, total_size

        return f, content_type, total_size

    def save_direct(
        self,
        object_key: str,
        file_data: BinaryIO,
        content_type: str,
        file_size: int,
    ) -> str:
        dest = self._full_path(object_key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, "wb") as f:
            shutil.copyfileobj(file_data, f)

        logger.info(
            "local_file_saved_direct",
            object_key=object_key,
            file_size=file_size,
            content_type=content_type,
        )
        return object_key

    def delete(self, object_key: str) -> None:
        path = self._full_path(object_key)
        if path.is_file():
            path.unlink()
            logger.info("local_file_deleted", key=object_key)
        else:
            logger.warning("local_file_not_found_for_delete", key=object_key)

    # ── Presigned URLs (local substitutes) ────────────────────

    def presigned_upload_url(
        self,
        org_id: str,
        filename: str,
        content_type: str,
        expires: int = 3600,
    ) -> dict:
        """For local storage, return an API endpoint URL instead of a presigned URL.

        The client will POST to ``/api/v1/storage/upload`` with the file.
        """
        object_key = self._generate_key(org_id, filename)
        return {
            "upload_url": f"/api/v1/storage/upload?object_key={object_key}",
            "object_key": object_key,
            "public_url": self.public_url(object_key),
            "content_type": content_type,
            "filename": filename,
        }

    def presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        return self.public_url(object_key)

    def public_url(self, object_key: str) -> str:
        return f"/api/v1/storage/files/{object_key}"

    # ── Local-only helpers ────────────────────────────────────

    def get_file_path(self, object_key: str) -> Path:
        """Return the absolute filesystem path for an object key.

        Used by the local file serving endpoint.
        """
        return self._full_path(object_key)

    @property
    def root(self) -> Path:
        return self._root
