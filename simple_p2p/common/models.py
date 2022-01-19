from abc import ABC
from enum import Enum
from typing import Optional


class FileStatus(str, Enum):
    READY = "ready"
    DOWNLOADING = "downloading"
    INVALID = "invalid"


class FileMetadata:
    # immutable
    name: str
    digest: str
    size: int
    path: str
    # mutable
    status: FileStatus
    current_size: int
    current_digest: str

    def __init__(self, data: dict = None):
        if data is not None:
            for key, value in data.items():
                if key == "status":
                    self.status = FileStatus[value.upper()]
                else:
                    setattr(self, key, value)

    def as_dict(self):
        return dict(
            name=self.name,
            path=self.path,
            digest=self.digest,
            size=self.size,
            status=self.status.value,
            current_size=self.current_size,
            current_digest=self.current_digest,
        )

    @property
    def is_valid(self):
        return self.size == self.current_size and self.digest == self.current_digest

    @property
    def can_share(self):
        return self.status == FileStatus.READY and self.is_valid


class AbstractController(ABC):
    def get_file(self, name) -> FileMetadata:
        pass

    def add_consumer(self, context):
        pass

    def remove_consumer(self, context, exc_type, exc_value):
        pass

    def add_provider(self, context):
        pass

    def remove_provider(self, context, exc_type, exc_value):
        pass

    def provider_update(self, context, bytes_downloaded: int):
        pass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]
