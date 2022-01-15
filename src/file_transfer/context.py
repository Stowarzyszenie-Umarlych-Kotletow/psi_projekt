from typing import Tuple, Optional

from file_transfer.models import FileProvider
from file_transfer.mock import FileInfo, Controller

class FileContext(FileProvider):
    def __init__(self, controller: Controller, file: FileInfo, endpoint: Optional[Tuple[str, int]]) -> None:
        self._controller = controller
        self._file = file
        self._should_stop = False
        self._endpoint = endpoint

    @property
    def should_stop(self):
        return self._should_stop

    @property
    def endpoint(self) -> Optional[Tuple[str, int]]:
        return self._endpoint

    @property
    def file(self) -> FileInfo:
        return self._file

    def stop(self):
        self._should_stop = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class FileConsumerContext(FileContext):
    def __enter__(self):
        self._controller.add_consumer(self)
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self._controller.remove_consumer(self)

class FileProviderContext(FileContext):
    def __enter__(self):
        self._controller.add_provider(self)
        return super(FileProviderContext, self).__enter__()

    def update(self, bytes_downloaded: int):
        self._controller.provider_update(self, bytes_downloaded)

    def __exit__(self, exc_type, exc_value, tb):
        self._controller.remove_provider(self, exc_value)
        return super(FileProviderContext, self).__exit__(exc_type, exc_value, tb)