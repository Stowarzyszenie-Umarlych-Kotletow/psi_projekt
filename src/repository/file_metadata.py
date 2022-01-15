from dataclasses import dataclass
from enum import Enum


class FileStatus(str, Enum):
    READY = "ready"
    DOWNLOADING = "downloading"
    SHARING = "sharing"


class FileMetadata:
    name: str
    path: str
    digest: str
    size: int
    status: FileStatus

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
        )
