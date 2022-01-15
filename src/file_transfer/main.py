import asyncio
from codecs import StreamReader, StreamWriter
from time import sleep
from typing import *
from common.config import MOCK_CONTROLLER_PATH
from file_transfer.mock import Controller, FileInfo
from file_transfer.server import ServerHandler
from file_transfer.client import ClientHandler
import threading

controller = Controller(MOCK_CONTROLLER_PATH)


async def handle_client(*args, **kwargs):
    handler = ServerHandler(controller)
    await handler.handle_client(*args, **kwargs)


async def handle_download(
    reader: StreamReader, writer: StreamWriter, file: FileInfo, offset: int
):
    handler = ClientHandler(controller, file, offset)
    await handler.handle_connection(reader, writer)


async def download(file: FileInfo, offset: int):
    await asyncio.sleep(2)
    (reader, writer) = await asyncio.open_connection('127.0.0.1', 1337)
    await handle_download(reader, writer, file, offset)
    print("Download complete")

def loop_worker(loop):
    asyncio.set_event_loop(loop)
    asyncio.get_event_loop().run_forever()

def new_loop():
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop_worker, args=(loop,), daemon=True)
    t.start()
    return loop

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 1337)
    async with server:
        await server.serve_forever()

#loop = new_loop()
#a=asyncio.run_coroutine_threadsafe(download(FileInfo('wideo.mkv', '/home/powerofdark/wideo.mkv', 0, '123'), 0), loop)
#_=asyncio.run_coroutine_threadsafe(main(), loop)
#sleep(100)