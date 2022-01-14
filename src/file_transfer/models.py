from abc import ABC, abstractmethod
from asyncio.streams import StreamReader, StreamWriter
from optparse import Option
from typing import *

from aiofile.utils import async_open
from file_transfer.exceptions import InvalidRangeError, ProtoError
from file_transfer.io_utils import calc_range_len
from file_transfer.mock import FileInfo
from file_transfer.parse_utils import *
from file_transfer.enums import ContentType, KnownHeader, ProtoMethod, ProtoStatusCode

TRequest = TypeVar("TRequest", bound="Request")


LINE_SEP = "\r\n"
ENCODING = "utf-8"


class SanitizingDict:
    def __init__(self, init_dict: dict = None, **kwargs) -> None:
        self.items: Dict[str, str] = {}
        if init_dict:
            for (k, v) in init_dict.items():
                self[k] = v
        for (k, v) in kwargs.items():
            self[k] = v

    def __setitem__(self, key: str, value: str):
        self.items[self.sanitize(key)] = value

    def __getitem__(self, key: str) -> str:
        return self.items[self.sanitize(key)]

    def get(self, key: str, default=None) -> Optional[str]:
        try:
            return self[self.sanitize(key)]
        except KeyError:
            return default

    def set_default(self, key: str, value: str):
        key = self.sanitize(key)
        current_value = self.get(key)
        if current_value is not None:
            return current_value
        self[key] = value
        return value

    def sanitize(self, value: str) -> str:
        return value


class DigestContainer(SanitizingDict):
    def sanitize(self, value: str) -> str:
        return value.lower()


class HeadersContainer(SanitizingDict):
    def sanitize(self, value: str) -> str:
        return KnownHeader.sanitize(value)

    @property
    def content_length(self) -> Optional[int]:
        value = self.get(KnownHeader.CONTENT_LENGTH, None)
        return None if value is None else int(value)

    @property
    def range(self) -> Optional[Tuple[str, Optional[int], Optional[int]]]:
        value = self.get(KnownHeader.RANGE, None)
        return None if value is None else parse_range_header(value)

    @property
    def content_range(self) -> Optional[Tuple[str, int, int, int]]:
        value = self.get(KnownHeader.CONTENT_RANGE)
        return None if value is None else parse_content_range_header(value)

    @property
    def if_digest(self) -> Optional[dict[str, str]]:
        value = self.get(KnownHeader.IF_DIGEST)
        return None if value is None else parse_kv_header(value)

    @property
    def digest(self) -> Optional[dict[str, str]]:
        value = self.get(KnownHeader.DIGEST)
        return None if value is None else parse_kv_header(value)

    @staticmethod
    async def read_from(
        reader: StreamReader, encoding: str = ENCODING
    ) -> "HeadersContainer":
        headers = HeadersContainer()
        while True:
            header = process_line(await reader.readline(), encoding, "Invalid header")
            if not header:
                break
            (key, value) = parse_header(header)
            headers[key] = value
        return headers

    def write_to(self, writer: StreamWriter, encoding: str):
        for (key, value) in self.items.items():
            writer.write(f"{key}: {value}{LINE_SEP}".encode(encoding))
        writer.write(LINE_SEP.encode(encoding))


class Request:
    def __init__(
        self, method: ProtoMethod, urn: str, headers: HeadersContainer
    ) -> None:
        self.method = method
        self.urn = urn
        self.headers = headers

    async def write_to(self, writer: StreamWriter, encoding: str = ENCODING):
        writer.write(f"{self.method.value} {self.urn}{LINE_SEP}".encode(encoding))
        self.headers.write_to(writer, encoding)
        await writer.drain()

    @classmethod
    async def read_from(
        cls: Type[TRequest], reader: StreamReader, encoding: str = ENCODING
    ) -> TRequest:
        request_line = process_line(
            await reader.readline(), encoding, "Invalid request line"
        )
        (method, urn) = parse_request_line(request_line)
        headers = await HeadersContainer.read_from(reader)

        request = cls(method=method, urn=urn, headers=headers)
        return request


class Response:
    def __init__(
        self,
        status_code: ProtoStatusCode,
        status_text: str = None,
        headers: HeadersContainer = None,
    ) -> None:
        self.status_code = status_code
        self.status_text = status_text or status_code.describe()
        self._headers = headers or HeadersContainer()

    @property
    def headers(self) -> HeadersContainer:
        return self._headers

    async def _write_body(self, writer: StreamWriter):
        pass

    async def write_to(
        self, writer: StreamWriter, encoding: str = ENCODING, include_body: bool = True
    ):
        writer.write(
            f"{self.status_code} {self.status_text}{LINE_SEP}".encode(encoding)
        )
        self._headers.write_to(writer, encoding)
        await writer.drain()
        if include_body:
            await self._write_body(writer)
            await writer.drain()

    def assert_ok(self):
        if not self.status_code.is_success:
            raise ProtoError(self.status_code)

    @staticmethod
    async def read_from(
        reader: StreamReader, encoding: str = ENCODING
    ) -> Tuple["Response", Optional[StreamReader]]:
        response_line = process_line(
            await reader.readline(), encoding, "Invalid status line"
        )
        (method, urn) = parse_request_line(response_line)
        headers = await HeadersContainer.read_from(reader)
        response = Response(method=method, urn=urn, headers=headers)

        content_stream = reader if response.content_length is not None else None

        return (response, content_stream)


class FileProvider(ABC):
    @property
    @abstractmethod
    def file(self) -> FileInfo:
        pass

    @property
    def should_stop(self) -> bool:
        return False

    def stop() -> None:
        pass


class ByteRange:
    def __init__(
        self, offset: Optional[int] = None, length: Optional[int] = None
    ) -> None:
        offset = offset or 0
        self._offset = offset
        self._length = length
        if (length and length < 0) or (offset and offset < 0):
            raise InvalidRangeError("Range specifiers cannot be negative")

    def get_effective_length(self, content_size: int) -> int:
        return calc_range_len(content_size, self.offset, self.length)

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def length(self) -> Optional[int]:
        return self._length

    @staticmethod
    def from_interval(start: Optional[int], end: Optional[int]) -> "ByteRange":
        offset = start or 0
        length = None
        if end:
            length = end - offset
        return ByteRange(offset, length)


class FileResponse(Response):
    def __init__(
        self,
        file_provider: FileProvider,
        range: ByteRange = None,
        chunk_size=16 * 1024,
        headers=None,
        **kwargs,
    ):
        headers = headers or HeadersContainer()
        range = range or ByteRange()

        self.file_provider = file_provider
        self.range = range
        self.chunk_size = chunk_size

        file = file_provider.file
        range_length = range.get_effective_length(file.size)

        status_code = ProtoStatusCode.C200_OK

        headers[KnownHeader.CONTENT_LENGTH] = str(range_length)
        headers.set_default(KnownHeader.CONTENT_TYPE, ContentType.OCTET_STREAM)

        if range_length != file.size:
            headers[
                KnownHeader.CONTENT_RANGE
            ] = f"bytes {self.range.offset}-{self.range.offset + range_length}/{file.size}"
            status_code = ProtoStatusCode.C206_PARTIAL_CONTENT
        if file.digest:
            headers[KnownHeader.DIGEST] = file.digest

        super().__init__(status_code=status_code, headers=headers, **kwargs)

    async def _write_body(self, writer: StreamWriter):
        fp: FileProvider
        content_length = self.headers.content_length
        with self.file_provider as fp:
            to_read = content_length
            async with async_open(fp.file.path, "rb") as file:
                file.seek(self.range.offset)
                while to_read > 0 and not fp.should_stop:
                    read_bytes = await file.read(min(self.chunk_size, to_read))
                    num_read_bytes = len(read_bytes)
                    if num_read_bytes == 0:
                        break
                    to_read -= num_read_bytes
                    writer.write(read_bytes)
                    await writer.drain()
                if to_read > 0:
                    print(
                        f"Expected {content_length} bytes, got {content_length - to_read}"
                    )
            await writer.drain()
