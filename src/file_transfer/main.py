import asyncio
from typing import *
from common.config import MOCK_CONTROLLER_PATH
from file_transfer.mock import Controller
from file_transfer.server import ClientHandler


controller = Controller(MOCK_CONTROLLER_PATH)


async def handle_client(*args, **kwargs):
    handler = ClientHandler(controller)
    await handler.handle_client(*args, **kwargs)


async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 1337)
    async with server:
        await server.serve_forever()


asyncio.run(main())
