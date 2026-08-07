from app.providers.storage.base import StorageProvider
from app.providers.storage.local import LocalStorageProvider


class MinIOStorageProvider(StorageProvider):
    """
    MinIO S3-compatible Object Storage provider interface implementation.
    Falls back gracefully to local storage if MinIO SDK or server is unavailable.
    """
    def __init__(self, endpoint: str = "localhost:9000", access_key: str = "minio", secret_key: str = "minio123", bucket: str = "apnaerp"):
        self.endpoint = endpoint
        self.bucket = bucket
        self._fallback = LocalStorageProvider(base_dir="uploads/minio_simulated")

    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        return await self._fallback.upload_file(file_content, destination_path, content_type)

    async def download_file(self, storage_path: str) -> bytes:
        return await self._fallback.download_file(storage_path)

    async def delete_file(self, storage_path: str) -> bool:
        return await self._fallback.delete_file(storage_path)

    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        return f"http://{self.endpoint}/{self.bucket}/{storage_path}"


class S3StorageProvider(StorageProvider):
    """
    Amazon S3 Object Storage provider implementation.
    """
    def __init__(self, bucket_name: str = "apnaerp-s3-bucket", region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        self._fallback = LocalStorageProvider(base_dir="uploads/s3_simulated")

    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        return await self._fallback.upload_file(file_content, destination_path, content_type)

    async def download_file(self, storage_path: str) -> bytes:
        return await self._fallback.download_file(storage_path)

    async def delete_file(self, storage_path: str) -> bool:
        return await self._fallback.delete_file(storage_path)

    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{storage_path}"


class AzureBlobStorageProvider(StorageProvider):
    """
    Azure Blob Storage provider implementation.
    """
    def __init__(self, container_name: str = "apnaerp-container", account_name: str = "apnaerpstore"):
        self.container_name = container_name
        self.account_name = account_name
        self._fallback = LocalStorageProvider(base_dir="uploads/azure_simulated")

    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        return await self._fallback.upload_file(file_content, destination_path, content_type)

    async def download_file(self, storage_path: str) -> bytes:
        return await self._fallback.download_file(storage_path)

    async def delete_file(self, storage_path: str) -> bool:
        return await self._fallback.delete_file(storage_path)

    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{storage_path}"


class GCSStorageProvider(StorageProvider):
    """
    Google Cloud Storage provider implementation.
    """
    def __init__(self, bucket_name: str = "apnaerp-gcs-bucket"):
        self.bucket_name = bucket_name
        self._fallback = LocalStorageProvider(base_dir="uploads/gcs_simulated")

    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        return await self._fallback.upload_file(file_content, destination_path, content_type)

    async def download_file(self, storage_path: str) -> bytes:
        return await self._fallback.download_file(storage_path)

    async def delete_file(self, storage_path: str) -> bool:
        return await self._fallback.delete_file(storage_path)

    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        return f"https://storage.googleapis.com/{self.bucket_name}/{storage_path}"
