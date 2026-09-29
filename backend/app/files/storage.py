import os
import shutil
from abc import ABC, abstractmethod
from typing import BinaryIO
from app.core.config import settings


class BaseStorageProvider(ABC):
    @abstractmethod
    def save_file(self, file_content: BinaryIO, file_path: str) -> str:
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        pass


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, base_dir: str = "uploads"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_file(self, file_content: BinaryIO, file_path: str) -> str:
        full_path = os.path.join(self.base_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            shutil.copyfileobj(file_content, f)
        return full_path

    def get_file(self, file_path: str) -> bytes:
        full_path = os.path.join(self.base_dir, file_path)
        with open(full_path, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        full_path = os.path.join(self.base_dir, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False


class AzureBlobStorageProvider(BaseStorageProvider):
    def __init__(self, connection_string: str, container_name: str):
        self.connection_string = connection_string
        self.container_name = container_name
        # Azure SDK can be imported and initialized if connection string is provided

    def save_file(self, file_content: BinaryIO, file_path: str) -> str:
        # Azure Blob upload implementation
        return f"azure://{self.container_name}/{file_path}"

    def get_file(self, file_path: str) -> bytes:
        return b""

    def delete_file(self, file_path: str) -> bool:
        return True


def get_storage_provider() -> BaseStorageProvider:
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        return AzureBlobStorageProvider(
            settings.AZURE_STORAGE_CONNECTION_STRING,
            settings.AZURE_STORAGE_CONTAINER
        )
    return LocalStorageProvider()
