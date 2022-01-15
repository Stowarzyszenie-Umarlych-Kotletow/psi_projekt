from cmath import log
from io import SEEK_SET
import logging
import os
from uuid import UUID, uuid4
from common.config import DIGEST_ALG
from file_transfer.mock import Controller, FileInfo
from asyncio.streams import StreamReader, StreamWriter
from typing import *
from file_transfer.enums import KnownHeader, ProtoMethod, ProtoStatusCode
from file_transfer.exceptions import (
    ProtoError,
)
from file_transfer.models import (
    HeadersContainer,
    Request,
    Response,
)
from file_transfer.context import FileConsumerContext, FileProviderContext
from logging import Logger
from aiofile.utils import async_open


class ClientHandler:
    def __init__(
        self, controller: Controller, file: FileInfo, endpoint: Optional[Tuple[str, int]]
    ) -> None:
        self._controller = controller
        self._id = uuid4()
        self._logger = logging.getLogger("ClientHandler")
        self._context = self.new_provider(file, endpoint)
        self.chunk_size = 16*1024

    def new_provider(self, file: FileInfo, endpoint) -> FileProviderContext:
        return FileProviderContext(self._controller, file, endpoint)

    async def handle_content(
        self, context: FileProviderContext, response: Response, reader: StreamReader
    ):
        file = context.file
        content_range = response.headers.content_range
        if content_range:
            (unit, file_offset, *_) = content_range
        else:
            file_offset = 0
        
        content_length = response.headers.content_length
        open(file.path, 'a').close()
        with open(file.path, 'rb+') as raw_file:
            async with async_open(raw_file) as writer:
                writer.seek(file_offset)
                while file_offset < content_length and not context.should_stop:
                    to_write = content_length - file_offset
                    read_bytes = await reader.read(min(self.chunk_size, to_write))
                    num_read_bytes = len(read_bytes)
                    if num_read_bytes == 0:
                        break
                    file_offset += num_read_bytes
                    await writer.write(read_bytes)
                    context.update(file_offset)
                raw_file.truncate(file_offset)
                if file_offset < content_length:
                    print(
                        f"Expected {content_length} bytes, got {file_offset}"
                    )
                    raise ProtoError(ProtoStatusCode.C500_SERVER_ERROR)

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        log_extra = dict(id=self._id, method="GET", urn=self._context.file.name)
        (ip, port) = writer.get_extra_info("peername")
        self._logger.debug("New connection to %s:%s", ip, port, extra=log_extra)

        try:
            with self._context as context:
                file = context.file
                file_offset = file.current_size
                headers = HeadersContainer()
                if file.digest:
                    headers[KnownHeader.IF_DIGEST] = f"{DIGEST_ALG}={file.digest}"
                if file_offset:
                    headers[KnownHeader.RANGE] = f"bytes {file_offset}-"

                request = Request(ProtoMethod.GET, file.name, headers)
                await request.write_to(writer)

                (response, content_reader) = await Response.read_from(reader)
                response.assert_ok()
                if not content_reader:
                    raise ProtoError(ProtoStatusCode.C404_NOT_FOUND)
                
                await self.handle_content(context, response, content_reader)
                return True
        except Exception as e:
            self._logger.warn("Download error", exc_info=e, extra=log_extra)
            raise e
        finally:
            writer.close()
        return False