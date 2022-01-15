import asyncio
import threading
from typing import List, Optional, Tuple, Dict

from common.config import TCP_PORT
from file_transfer.client import ClientHandler
from file_transfer.exceptions import MessageError
from file_transfer.mock import FileInfo
from file_transfer.server import ServerHandler
from repository.file_metadata import FileMetadata
from repository.repository import NotFoundError, Repository
from udp.udp_controller import UdpController
from file_transfer.main import new_loop, in_background
from concurrent.futures import Future, ThreadPoolExecutor
from file_transfer.context import FileConsumerContext, FileProviderContext


class FileStateContext:
    def __init__(self, file_meta: FileMetadata) -> None:
        self._file_meta = file_meta
        self._lock = threading.Lock()
        self._provider: Optional[FileProviderContext] = None
        self._consumers: List[FileConsumerContext] = []

    @property
    def file_meta(self) -> FileMetadata:
        return self._file_meta

    @property
    def consumers(self) -> List[FileConsumerContext]:
        return self._consumers

    @property
    def provider(self) -> Optional[FileProviderContext]:
        return self._provider

    @provider.setter
    def provider(self, value):
        with self._lock:
            provider = self._provider
            if provider and value:
                raise MessageError("Provider already exists")
            self._provider = value

    def add_consumer(self, context):
        self._consumers.append(context)

    def remove_consumer(self, context):
        self._consumers.remove(context)


class Controller:
    def __init__(self):
        self._udp_controller = UdpController(self)
        self._state: Dict[str, FileStateContext] = {}
        self._repo = Repository()
        self._loop = new_loop()

    def start(self):
        self._udp_controller.start()
        self._server_task: Future = asyncio.run_coroutine_threadsafe(
            self._serve_tcp(), self._loop
        )
        self._repo.load()
        self._load_from_repo()

    def _load_from_repo(self):
        repo_files = self._repo.get_files()
        for (name, meta) in repo_files.items():
            self._add_file(meta)

    def _add_file(self, meta: FileMetadata):
        # TODO: Collisions
        self._state[meta.name] = FileStateContext(meta)

    async def _handle_client(self, reader, writer):
        handler = ServerHandler(self)
        await handler.handle_client(reader, writer)

    async def _download_from(self, file: FileMetadata, endpoint: Tuple[str, int]):
        try:
            streams = await asyncio.open_connection(*endpoint)
            handler = ClientHandler(self, file, endpoint)
            await handler.handle_connection(*streams)

            await self._loop.run_in_executor(None, self._repo.update_stat, file.name)
            # TODO: update file
            print(f"Download completed, digest={file.digest}, cur_digest={file.current_digest}")
            await self._loop.run_in_executor(None, self._repo.change_state, file.name, 'READY')
        except:
            # TODO: handle errors
            pass

    async def _serve_tcp(self):
        server = await asyncio.start_server(self._handle_client, "0.0.0.0", TCP_PORT)
        async with server:
            await server.serve_forever()

    def schedule_download(self, name: str, digest: Optional[str], size: int, endpoint: Tuple[str, int]):
        # TODO: check state
        meta = self._repo.init_meta(name, digest, size)
        self._add_file(meta)
        in_background(asyncio.run_coroutine_threadsafe(self._download_from(meta, endpoint), self._loop))
        print("Download scheduled")

    def stop(self):
        self._udp_controller.stop()
        # TODO: handle tcp

    def get_peers(self):
        return self._udp_controller.get_peers()

    def get_peer(self, ip) -> "TODO":
        return self._udp_controller.get_peer(ip)

    def search_file(self, file_name: str = None, file_hash: str = None) -> dict:
        return self._udp_controller.search(file_name, file_hash)

    def _get_file_state(self, name: str) -> FileStateContext:
        try:
            return self._state[name]
        except KeyError:
            raise NotFoundError(f"File '{name}' not found in repository")

    def get_file(self, name) -> FileMetadata:
        return self._get_file_state(name).file_meta

    def add_consumer(self, context):
        return self._get_file_state(context.file.name).add_consumer(context)

    def remove_consumer(self, context):
        return self._get_file_state(context.file.name).remove_consumer(context)

    def add_provider(self, context):
        self._get_file_state(context.file.name).provider = context

    def provider_update(self, context, bytes_downloaded: int):
        self._get_file_state(
            context.file.name
        ).file_meta.current_size = bytes_downloaded
        # TODO: yeah..

    def remove_provider(self, context, exc_value: Optional[Exception] = None):
        state = self._get_file_state(context.file.name)
        state.provider = None
        # TODO: refresh state?

    def add_file(self, path):
        self._repo.add_file(path)

