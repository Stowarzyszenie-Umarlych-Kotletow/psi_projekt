import asyncio
from file_transfer.mock import FileInfo
from file_transfer.server import ServerHandler
from udp.udp_controller import UdpController
from file_transfer.main import new_loop, in_background
from concurrent.futures import Future

class FileStateContext:
    pass

class Controller:
    def __init__(self):
        self._udp_controller = UdpController()
        self._loop = new_loop()

    def start(self):
        self._udp_controller.start()
        self._server_task: Future = asyncio.run_coroutine_threadsafe(self._serve_tcp(), self._loop)

    async def handle_client(self, *args, **kwargs):
        handler = ServerHandler(self)
        await handler.handle_client(*args, **kwargs)

    async def _serve_tcp(self):
        server = await asyncio.start_server(self.handle_client, "0.0.0.0", 1337)
        async with server:
            await server.serve_forever()

    def stop(self):
        self._udp_controller.stop()
        # TODO: handle tcp

    def get_peers(self):
        return self._udp_controller.get_peers()

    def search_file(self, file_name: str = None, file_hash: str = None) -> dict:
        return self._udp_controller.search(file_name, file_hash)

    async def _download_from(self, file: FileInfo, offset: int):


    def get_file(self, name) -> FileInfo:
        pass

    def add_consumer(self, context):
        pass

    def remove_consumer(self, context):
        pass
    
    def add_provider(self, context):
        pass

    def provider_update(self, context, bytes_downloaded: int):
        pass


