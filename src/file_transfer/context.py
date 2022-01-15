from file_transfer.models import FileProvider
from file_transfer.mock import FileInfo, Controller

class FileContext(FileProvider):
    def __init__(self, controller: Controller, file: FileInfo) -> None:
        self.controller = controller
        self._file = file
        self._should_stop = False

    @property
    def should_stop(self):
        return self._should_stop

    @property
    def file(self) -> FileInfo:
        return self._file

    def stop(self):
        self._should_stop = True

class FileConsumerContext(FileContext):
    def __enter__(self):
        self.controller.add_consumer(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.controller.remove_consumer(self)

class FileProviderContext(FileContext):
    def __enter__(self):
        self.controller.add_provider(self)
        return self

    def update(self, bytes_downloaded: int):
        self.controller.provider_update(self, bytes_downloaded)

    def __exit__(self, exc_type, exc_value, tb):
        self.controller.remove_provider(self, exc_value)