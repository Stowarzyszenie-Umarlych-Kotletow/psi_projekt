from typing import *
from enum import Enum

STATUS_DESCRIPTIONS = {
    200: "OK",
    206: "Partial content",
    400: "Bad request",
    404: "Not found",
    412: "Precondition failed",
    416: "Invalid range",
    500: "Server error",
}


class ProtoStatusCode(int, Enum):
    C200_OK = 200
    C206_PARTIAL_CONTENT = 206
    C400_BAD_REQUEST = 400
    C404_NOT_FOUND = 404
    C412_PRECONDITION_FAILED = 412
    C416_INVALID_RANGE = 416
    C500_SERVER_ERROR = 500

    @property
    def is_success(self) -> bool:
        return 200 <= self.value <= 299

    def describe(self) -> str:
        return STATUS_DESCRIPTIONS.get(self.value, self.name)

    @classmethod
    def is_valid(cls, code: str):
        try:
            code_int = int(code)
            return 100 <= code_int <= 599
        except ValueError:
            return False


class ValidatingEnum(Enum):
    @classmethod
    def is_valid(cls, method):
        return cls.sanitize(method) in cls._value2member_map_.keys()

    @classmethod
    def get(cls, method: str):
        return cls[cls.sanitize(method)]

    @classmethod
    def sanitize(cls, value: str) -> str:
        return value


class ProtoMethod(str, ValidatingEnum):
    GET = "GET"
    HEAD = "HEAD"

    @classmethod
    def sanitize(cls, method: str) -> str:
        return method.upper()


class KnownHeader(str, ValidatingEnum):
    CONTENT_LENGTH = "content-length"
    CONTENT_TYPE = "content-type"
    IF_DIGEST = "if-digest"
    DIGEST = "digest"
    RANGE = "range"
    CONTENT_RANGE = "content-range"

    @classmethod
    def sanitize(cls, header: str) -> str:
        return header.lower()


class ContentType(str, ValidatingEnum):
    OCTET_STREAM = "application/octet-stream"

    @classmethod
    def sanitize(cls, header: str) -> str:
        return header.lower()
