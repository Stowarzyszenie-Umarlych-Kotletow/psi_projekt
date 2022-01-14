from dataclasses import dataclass


@dataclass
class FileMetadata:
    name: str
    path: str
    hash: str
    size: int
    status: str

    def __init__(self, data=None):
        if data is not None:
            for key, value in data.items():
                setattr(self, key, value)

    def as_dict(self):
        return dict(
            name=self.name,
            path=self.path,
            hash=self.hash,
            size=self.size,
            status=self.status,
        )
