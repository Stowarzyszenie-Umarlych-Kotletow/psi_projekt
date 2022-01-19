from asyncio import wait_for
import logging
from uuid import UUID, uuid4
from asyncio.streams import StreamReader, StreamWriter
from typing import *
from logging import Logger
from aiofile.utils import async_open

from simple_p2p.common.config import (
    DIGEST_ALG,
    FILE_CHUNK_SIZE,
    TCP_FILE_RECEIVE_TIMEOUT,
)
from simple_p2p.common.exceptions import LogicError
from simple_p2p.common.models import AbstractController, FileMetadata
from simple_p2p.file_transfer.enums import KnownHeader, ProtoMethod, ProtoStatusCode
from simple_p2p.file_transfer.exceptions import ProtoError
from simple_p2p.file_transfer.models import (
    HeadersContainer,
    Request,
    Response,
)
from simple_p2p.file_transfer.context import FileConsumerContext, FileProviderContext


class ClientHandler:
    def __init__(self, context: FileProviderContext) -> None:
        self._id = uuid4()
        self._logger = logging.getLogger("ClientHandler")
        self._context = context
        self.chunk_size = FILE_CHUNK_SIZE

    async def handle_content(self, response: Response, reader: StreamReader):
        context = self._context
        file = context.file
        content_length = response.headers.content_length
        content_range = response.headers.content_range
        if content_range:
            (unit, file_offset, file_until, content_length) = content_range
        else:
            file_offset = 0

        open(file.path, "a").close()  # create if it doesn't exist
        with open(file.path, "rb+") as file_raw:
            async with async_open(file_raw) as writer:
                writer.seek(file_offset)
                while file_offset < content_length and not context.should_stop:
                    to_write = content_length - file_offset
                    read_bytes = await wait_for(
                        reader.read(min(self.chunk_size, to_write)),
                        TCP_FILE_RECEIVE_TIMEOUT,
                    )
                    num_read_bytes = len(read_bytes)
                    if num_read_bytes == 0:
                        break
                    file_offset += num_read_bytes
                    await writer.write(read_bytes)
                    context.update(file_offset)
                file_raw.truncate(file_offset)
            if file_offset < content_length:
                raise LogicError(f"Expected {content_length} bytes, got {file_offset}")

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        context = self._context
        log_extra = dict(id=self._id, method="GET", uri=context.file.name)
        (ip, port) = writer.get_extra_info("peername")
        self._logger.debug("New connection to %s:%s", ip, port, extra=log_extra)

        try:
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

            await self.handle_content(response, content_reader)
        except Exception as exc:
            self._logger.warning("Download error", exc_info=exc, extra=log_extra)
            raise exc
        finally:
            writer.close()
