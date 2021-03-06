import asyncio
import logging
from asyncio import run_coroutine_threadsafe, start_server
import random
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import List, Optional, Tuple, Dict

from simple_p2p.common.config import FILE_WATCHER_PERIOD, Config, MAX_FILENAME_LENGTH
from simple_p2p.common.models import AbstractController, FileMetadata, FileStatus
from simple_p2p.file_transfer.client import ClientHandler
from simple_p2p.file_transfer.context import FileConsumerContext, FileProviderContext
from simple_p2p.common.exceptions import (
    FileDuplicateException,
    LogicError,
    FileNameTooLongException,
    NotFoundError
)
from simple_p2p.common.tasks import coro_in_background, new_loop, in_background
from simple_p2p.file_transfer.exceptions import InconsistentFileStateError
from simple_p2p.file_transfer.server import ServerHandler
from simple_p2p.repository.repository import Repository
from simple_p2p.udp.found_response import FoundResponse
from simple_p2p.udp.peer import Peer
from simple_p2p.udp.udp_controller import UdpController


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
                raise LogicError("Provider already exists")
            self._provider = value

    def add_consumer(self, context):
        if not self.file_meta.can_share:
            raise NotFoundError("File is not accessible")
        with self._lock:
            self._consumers.append(context)

    def remove_consumer(self, context):
        with self._lock:
            self._consumers.remove(context)

    def clear(self):
        with self._lock:
            if self._provider:
                self._provider.stop()
            for consumer in self._consumers:
                consumer.stop()


class Controller(AbstractController):
    def __init__(self):
        self._udp_controller = UdpController(self)
        self._state: Dict[str, FileStateContext] = {}
        self._repo = Repository()
        self._loop: asyncio.AbstractEventLoop = None
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor()
        self._logger = logging.getLogger("Controller")
        self._tcp_server: asyncio.AbstractServer = None

    def start(self):
        cfg = Config()
        self._logger.info("Starting...")
        # create a new asyncio loop
        # to be used in the file monitor and TCP server
        self._loop = new_loop()
        try:
            self._repo.load()
            self._load_from_repo()
        except Exception as exc:
            raise LogicError(f"Failed to load the file repository: {exc}")

        try:
            self._udp_controller.start()
        except Exception as exc:
            raise LogicError(f"Failed to start the UDP controller: {exc}")
        try:
            # run the coroutine while catching the exceptions
            self._tcp_server: asyncio.AbstractServer = run_coroutine_threadsafe(
                start_server(self._handle_client, cfg.bind_ip, cfg.tcp_port), self._loop
            ).result()
        except Exception as exc:
            raise LogicError(f"Failed to start the TCP server")

        self._server_task: Future = run_coroutine_threadsafe(
            self._serve_tcp(), self._loop
        )
        self._monitor_task: Future = run_coroutine_threadsafe(
            self._monitor_files(), self._loop
        )

        self._logger.info("Ready")

    def _load_from_repo(self):
        """
        Internal function: loads files from repos
        Does not perform locking.
        """
        repo_files = self._repo.get_files()
        for meta in repo_files.values():
            self._add_file(meta)

    def _add_file(self, meta: FileMetadata):
        """
        Internal function: adds a file metadata to current state
        Performs locking.
        """
        self._logger.debug("Adding file %s", meta.name)
        with self._lock:
            if meta.name in self._state:
                self._logger.warning("Attempted to add duplicate file %s", meta.name)
                raise FileDuplicateException(f"File '{meta.name}' already exists")
            self._state[meta.name] = FileStateContext(meta)

    def _get_file_state(self, name: str) -> FileStateContext:
        """
        Internal function: returns file state by name
        Does not perform locking.
        """
        try:
            return self._state[name]
        except KeyError:
            raise NotFoundError(f"File '{name}' not found in repository")

    async def _handle_client(self, reader, writer):
        handler = ServerHandler(self)
        await handler.handle_client(reader, writer)

    async def _download_from(self, file: FileMetadata, endpoint: Tuple[str, int]):
        """
        Internal function: Handles a scheduled download
        """
        try:
            self._logger.info(
                "Starting download of file %s from %s", file.name, endpoint[0]
            )
            streams = await asyncio.open_connection(*endpoint)
            with FileProviderContext(self, file, endpoint) as context:
                handler = ClientHandler(context)
                await handler.handle_connection(*streams)

                await self._loop.run_in_executor(
                    self._executor, self._repo.update_stat, file.name
                )

                self._logger.info("Download of %s completed", file.name)
                if not file.is_valid:
                    raise LogicError("Invalid file download")

                await self._loop.run_in_executor(
                    self._executor, self._repo.change_state, file.name, "READY"
                )
        except Exception as exc:
            self._logger.warning("Download of %s failed", file.name, exc_info=exc)
            self._udp_controller.remove_peer(endpoint[0])

    async def _serve_tcp(self):
        """
        Internal function: runs the TCP server, forever
        """
        server = self._tcp_server
        async with server:
            await server.serve_forever()

    async def _monitor_files(self):
        """
        Internal function: monitors and updates file states, forever
        """
        def process_file(file: FileStateContext):
            meta = file.file_meta
            if meta.status == FileStatus.DOWNLOADING and not file.provider:
                if (
                    meta.current_size >= meta.size
                    and meta.digest != meta.current_digest
                ):
                    self._logger.warning("Truncating download %s", meta.name)
                    meta.current_size = 0
                coro_in_background(self.retry_download(meta.name), self._loop)

            elif meta.status == FileStatus.READY and not meta.is_valid:
                self._logger.warning("Invalidating file %s", meta.name)
                self._executor.submit(self._repo.change_state, meta.name, "INVALID")

        while True:
            await asyncio.sleep(FILE_WATCHER_PERIOD)
            with self._lock:
                for file in self._state.values():
                    process_file(file)

    async def retry_download(self, name: str):
        """
        Attempts to retry download of file `name`
        """
        self._logger.info("Retrying file %s", name)
        meta = self.get_file(name)
        search_res = await self._udp_controller.search(meta.name, meta.digest)
        responses = search_res.get(meta.digest, [])
        if len(responses) == 0:
            self._logger.warning("Cannot find hosts to resume file %s", name)
            return
        response = random.choice(search_res[meta.digest])
        peer = self._udp_controller.get_peer_by_ip(response.provider_ip)
        peer_port = peer.tcp_port
        await self._download_from(meta, (response.provider_ip, peer_port))

    def schedule_download(
        self, name: str, digest: Optional[str], size: int, endpoint: Tuple[str, int]
    ):
        """
        Schedule a file with given `name` and optionally `digest`
        to be downloaded from `endpoint`. Runs in background.
        """
        meta = self._repo.init_meta(name, digest, size)
        self._add_file(meta)
        coro_in_background(self._download_from(meta, endpoint), self._loop)

    def invalidate_file(self, name: str) -> Future:
        """
        Changes the state of file `name` to INVALID
        """
        return in_background(
            self._loop.run_in_executor(
                self._executor, self._repo.change_state, name, "INVALID"
            )
        )

    def is_running(self):
        return self._loop.is_running()

    def stop(self):
        self._logger.info("Stopping daemon...")
        with self._lock:
            if self._tcp_server:
                self._tcp_server.close()
            for state in self._state.values():
                state.clear()
            self._state = {}
            self._logger.debug("Stopping UDP controller...")
            self._udp_controller.stop()
            self._logger.debug("Stopping Controller loop...")
            self._loop.stop()

    def get_peer_by_ip(self, ip) -> Peer:
        return self._udp_controller.get_peer_by_ip(ip)

    async def search_file(
        self, name: str = None, digest: str = None
    ) -> Dict[str, List[FoundResponse]]:
        """
        Searches for a file `name` with optional `digest`.
        This is a coroutine, it might take a few seconds to run.
        """
        return await self._udp_controller.search(name, digest)


    def get_file(self, name) -> FileMetadata:
        if len(name) > MAX_FILENAME_LENGTH:
            raise FileNameTooLongException(
                f"File name exceeds {MAX_FILENAME_LENGTH} characters"
            )
        return self._get_file_state(name).file_meta

    def add_consumer(self, context):
        return self._get_file_state(context.file.name).add_consumer(context)

    def remove_consumer(self, context, exc_type, exc_value):
        state = self._get_file_state(context.file.name)
        if exc_value and (exc_type in [InconsistentFileStateError, FileNotFoundError]):
            # Handle the case when the file state is corrupted
            self.invalidate_file(state.file_meta.name)
        return state.remove_consumer(context)

    def add_provider(self, context):
        self._get_file_state(context.file.name).provider = context

    def provider_update(self, context, bytes_downloaded: int):
        self._get_file_state(
            context.file.name
        ).file_meta.current_size = bytes_downloaded

    def remove_provider(self, context, exc_type=None, exc_value=None):
        state = self._get_file_state(context.file.name)
        state.provider = None

    def add_file(self, path):
        """
        Adds external file from `path` into the repository
        This method locks implicitly
        """
        meta = self._repo.add_file(path)
        self._add_file(meta)
        return meta

    def remove_file(self, name):
        """
        Removes file `name` from the repository
        This method locks explicitly
        """
        with self._lock:
            state = self._get_file_state(name)
            self._repo.remove_file(name)
            state.clear()
            del self._state[name]

    @property
    def state(self):
        return self._state

    @property
    def known_peers(self):
        return self._udp_controller.known_peers

    @property
    def known_peers_list(self):
        return self._udp_controller.known_peers_list

    @property
    def repository_path(self):
        return self._repo.path
