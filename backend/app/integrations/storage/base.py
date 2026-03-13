"""Abstract base class for storage backends."""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    """Pluggable storage backend interface.

    Implementations:
      - LocalStorageBackend: local filesystem (development)
      - MinIOStorageBackend: MinIO / S3-compatible (production)
    """

    @abstractmethod
    def upload(
        self,
        org_id: str,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        file_size: int,
    ) -> str:
        """Upload a file and return the object key."""

    @abstractmethod
    def download(self, object_key: str) -> tuple[BinaryIO, str, int]:
        """Download a file.

        Returns:
            (data_stream, content_type, content_length)
            Caller MUST close the stream after consumption.
        """

    @abstractmethod
    def download_range(
        self, object_key: str, offset: int = 0, length: int = 0
    ) -> tuple[BinaryIO, str, int]:
        """Download a byte range of a file.

        Returns:
            (data_stream, content_type, total_size)
            total_size is the full object size (for Content-Range header).
        """

    @abstractmethod
    def delete(self, object_key: str) -> None:
        """Delete a file by object key."""

    @abstractmethod
    def presigned_upload_url(
        self,
        org_id: str,
        filename: str,
        content_type: str,
        expires: int = 3600,
    ) -> dict:
        """Generate a presigned PUT URL for direct client-side upload.

        Returns:
            dict with upload_url, object_key, public_url, content_type, filename.
        """

    @abstractmethod
    def presigned_download_url(self, object_key: str, expires: int = 3600) -> str:
        """Generate a presigned GET URL for downloading a file."""

    @abstractmethod
    def public_url(self, object_key: str) -> str:
        """Return the public-facing URL for a stored object."""
