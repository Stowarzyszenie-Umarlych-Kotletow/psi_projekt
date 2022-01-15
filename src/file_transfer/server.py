from cmath import log
import logging
from uuid import UUID, uuid4
from common.config import DIGEST_ALG
from file_transfer.mock import Controller, FileInfo
from asyncio.streams import StreamReader, StreamWriter
from typing import *
from file_transfer.enums import ProtoMethod, ProtoStatusCode
from file_transfer.exceptions import InvalidRangeError, ParseError, UnsupportedError
from file_transfer.models import (
    ByteRange,
    DigestContainer,
    FileResponse,
    Request,
    Response,
)
from file_transfer.context import FileConsumerContext
from logging import Logger

class ServerHandler:
    def __init__(self, controller: Controller) -> None:
        self._controller = controller
        self._id = uuid4()
        self._logger = logging.getLogger("ServerHandler")

    def new_consumer(self, file: FileInfo, endpoint: Optional[Tuple[str, int]]) -> FileConsumerContext:
        return FileConsumerContext(self._controller, file, endpoint)

    async def handle_request(self, request: Request, endpoint: Tuple[str, int]):
        range: ByteRange = None
        digest: str = None
        range_raw = request.headers.range
        if range_raw:
            (unit, start, end) = range_raw
            if unit != "bytes":
                raise UnsupportedError(f"Unsupported range unit: '{unit}'")
            range = ByteRange.from_interval(start, end)

        file = self._controller.get_file(request.urn)

        if_digest = request.headers.if_digest
        if if_digest:
            digest = DigestContainer(if_digest).get(DIGEST_ALG, None)
            if not digest:
                raise UnsupportedError(f"No supported algorithm found in if-digest.")
            if digest != file.digest:
                return Response(ProtoStatusCode.C412_PRECONDITION_FAILED)

        provider = self.new_consumer(file, endpoint)
        return FileResponse(provider, range)

    async def handle_client(self, reader: StreamReader, writer: StreamWriter):
        (ip, port) = writer.get_extra_info("peername")
        log_extra = dict(id=self._id, method="", urn="")
        self._logger.debug("New connection from %s:%s", ip, port, extra=log_extra)

        async def error_response(code: ProtoStatusCode, exc: Exception, **kwargs):
            self._logger.warn("Response error", exc_info=exc, extra=log_extra)
            return await write_response(Response(code), **kwargs)

        async def write_response(response: Response, **kwargs):
            self._logger.info(
                "Response code=%s len=%s",
                response.status_code.value,
                response.headers.content_length,
                extra=log_extra,
            )
            return await response.write_to(writer, **kwargs)

        request: Request = None
        response: Response = None
        try:

            try:
                request = await Request.read_from(reader)
            except (ValueError, ParseError) as e:
                return await error_response(ProtoStatusCode.C400_BAD_REQUEST, e)
            except Exception as e:
                return await error_response(ProtoStatusCode.C500_SERVER_ERROR, e)
            log_extra["method"] = request.method.value
            log_extra["urn"] = request.urn
            try:
                response = await self.handle_request(request, (ip, port))
            except UnsupportedError as e:
                return await error_response(ProtoStatusCode.C400_BAD_REQUEST, e)
            except InvalidRangeError as e:
                return await error_response(ProtoStatusCode.C416_INVALID_RANGE, e)
            except FileNotFoundError as e:
                return await error_response(ProtoStatusCode.C404_NOT_FOUND, e)
            except Exception as e:
                return await error_response(ProtoStatusCode.C500_SERVER_ERROR, e)

            include_body = request.method == ProtoMethod.GET
            await write_response(response, include_body=include_body)

        except Exception as outerException:
            self._logger.exception(
                "Uncaught exception", exc_info=outerException, extra=log_extra
            )
        finally:
            await writer.drain()
            writer.close()
