import os


class FileInfo:
    def __init__(self, path: str, size: int, digest: str) -> None:
        self.path = path
        self.size = size
        self.digest = digest


class Controller:
    def __init__(self, directory) -> None:
        self.directory = directory

    def find_file(self, urn) -> FileInfo:
        path = os.path.join(self.directory, urn)
        stat = os.stat(path)
        digest = "123"
        return FileInfo(path, stat.st_size, digest)

    def add_consumer(self, context):
        pass

    def remove_consumer(self, context):
        pass
