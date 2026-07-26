import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.core.storage.base_provider import StorageProvider

logger = logging.getLogger("app.storage.local")


class LocalStorageProvider(StorageProvider):
    """
    Local Filesystem Storage Provider.
    Organizes files into date-based subdirectories (uploads/YYYY/MM/DD/uuid.ext).
    """
    def __init__(self, base_dir: str = settings.UPLOAD_DIR):
        self.base_path = Path(base_dir).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitizes input filename removing unsafe characters.
        """
        filename = os.path.basename(filename)
        # Keep alphanumeric, dots, underscores, dashes
        cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
        return cleaned or "unnamed_file"

    def _get_date_subfolder(self) -> str:
        """
        Generates date subfolder path string YYYY/MM/DD.
        """
        now = datetime.now(timezone.utc)
        return os.path.join(f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}")

    async def save_file(self, file_data: bytes, stored_filename: str, subfolder: str = "") -> str:
        """
        Saves file bytes to local disk in uploads/YYYY/MM/DD/ and returns relative path.
        """
        date_folder = subfolder or self._get_date_subfolder()
        full_dir = self.base_path / date_folder
        full_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = self.sanitize_filename(stored_filename)
        file_path = full_dir / safe_filename

        with open(file_path, "wb") as f:
            f.write(file_data)

        # Return relative storage path
        relative_path = os.path.join(date_folder, safe_filename).replace("\\", "/")
        logger.info(f"[LocalStorage] Saved file to relative path: {relative_path}")
        return relative_path

    async def get_file(self, storage_path: str) -> bytes:
        """
        Reads file bytes from local disk.
        """
        full_path = self.base_path / storage_path
        if not full_path.exists() or not full_path.is_file():
            raise FileNotFoundError(f"Physical file not found at path: {storage_path}")

        with open(full_path, "rb") as f:
            return f.read()

    async def delete_file(self, storage_path: str) -> bool:
        """
        Deletes physical file from local disk.
        """
        full_path = self.base_path / storage_path
        if full_path.exists() and full_path.is_file():
            os.remove(full_path)
            logger.info(f"[LocalStorage] Deleted physical file: {storage_path}")
            return True
        return False

    async def file_exists(self, storage_path: str) -> bool:
        """
        Checks if file exists on local disk.
        """
        full_path = self.base_path / storage_path
        return full_path.exists() and full_path.is_file()


local_storage_provider = LocalStorageProvider()
