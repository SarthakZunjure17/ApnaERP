from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class StorageProvider(ABC):
    """
    Abstract StorageProvider interface for pluggable file storage backends.
    Allows zero-code-change switching between Local, MinIO, S3, Azure Blob, and GCS.
    """

    @abstractmethod
    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        """Uploads raw bytes to storage destination path. Returns internal storage path."""
        pass

    @abstractmethod
    async def download_file(self, storage_path: str) -> bytes:
        """Downloads file content as bytes from storage path."""
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """Deletes file at storage path. Returns True if deleted."""
        pass

    @abstractmethod
    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        """Generates a downloadable URL or pre-signed URL."""
        pass
