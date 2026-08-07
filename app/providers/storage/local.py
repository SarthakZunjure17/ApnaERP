import os
from app.providers.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider implementation.
    """
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    async def upload_file(self, file_content: bytes, destination_path: str, content_type: str) -> str:
        full_path = os.path.join(self.base_dir, destination_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_content)
        return destination_path

    async def download_file(self, storage_path: str) -> bytes:
        full_path = os.path.join(self.base_dir, storage_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Local file not found at path: {storage_path}")
        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, storage_path: str) -> bool:
        full_path = os.path.join(self.base_dir, storage_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    async def get_public_url(self, storage_path: str, expires_in_seconds: int = 3600) -> str:
        return f"/api/v1/storage/download/{storage_path}"
