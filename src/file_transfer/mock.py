import os
from typing import Optional


class FileInfo:
    def __init__(
        self, name: str, path: str, size: int, digest: str, current_size: int
    ) -> None:
        self.name = name
        self.path = path
        self.size = size
        self.digest = digest
        self.current_size = current_size


class Controller:
    def __init__(self, directory) -> None:
        self.directory = directory

    def get_file(self, name) -> FileInfo:
        path = os.path.join(self.directory, name)
        stat = os.stat(path)
        digest = "123"
        return FileInfo(name, path, stat.st_size, digest)

    def add_consumer(self, context):
        pass

    def remove_consumer(self, context):
        pass

    def add_provider(self, context):
        pass

    def remove_provider(self, context, exc: Optional[Exception]):
        pass

    def provider_update(self, context, bytes_downloaded: int):
        pass
