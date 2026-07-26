from abc import ABC, abstractmethod


class StorageProvider(ABC):
    """
    Abstract Base Class establishing contract for storage drivers (Local, AWS S3, Azure, GCS).
    """
    @abstractmethod
    async def save_file(self, file_data: bytes, stored_filename: str, subfolder: str = "") -> str:
        """
        Saves file bytes to physical storage and returns relative storage_path.
        """
        pass

    @abstractmethod
    async def get_file(self, storage_path: str) -> bytes:
        """
        Retrieves file bytes from storage by storage_path.
        """
        pass

    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Deletes physical file from storage by storage_path.
        """
        pass

    @abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """
        Checks whether a file exists in physical storage.
        """
        pass
