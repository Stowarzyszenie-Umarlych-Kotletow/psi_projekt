from typing import Tuple, Optional

import re
from simple_p2p.file_transfer.enums import ProtoMethod, KnownHeader, ProtoStatusCode
from simple_p2p.common.exceptions import ParseError


def rstrip_once(str: str) -> str:
    """
    Strips line separators in the specified line buffer
    """
    if not str:
        return str
    if str.endswith("\r\n"):
        return str[:-2]
    if str.endswith("\n"):
        return str[:-1]
    return str


def process_line(value: bytes, encoding: str, error_msg: str) -> str:
    """
    Decodes a line of text and strips whitespace characters
    """
    if not value:
        raise ParseError(error_msg)
    value = rstrip_once(value.decode(encoding))
    return value


def parse_header(line: str) -> Tuple[str, str]:
    """
    Parses the protocol header, separated by `: `
    """
    split = line.split(": ", 1)
    if len(split) != 2:
        raise ParseError("Missing header separator")
    (key, value) = split
    return (KnownHeader.sanitize(key.lstrip()), value)


def parse_range_header(value: str) -> Tuple[str, Optional[int], Optional[int]]:
    """
    Parses the range header of form
    `<unit:str> <start:int>-<end:int>`
    """
    pattern = r"(\S+) (\d*)-(\d*)"
    match = re.match(pattern, value)
    if not match:
        raise ParseError("Invalid range header")
    (unit, start, end) = match.groups()
    start = int(start) if start else None
    end = int(end) if end else None
    return (unit, start, end)


def parse_content_range_header(value: str) -> Tuple[str, int, int, int]:
    """
    Parses the content-range header of form
    `<unit:str> <start:int>-<end:int>/<full:int>`
    """
    pattern = r"(\S+) (\d+)-(\d+)/(\d+)"
    match = re.match(pattern, value)
    if not match:
        raise ParseError("Invalid content range header")
    (unit, start, end, full) = match.groups()
    return (unit, int(start), int(end), int(full))


def parse_kv_header(value: str) -> dict[str, Optional[str]]:
    """
    Parses a key-value header of form
    `key=value`
    """
    pattern = r"(\S+)=(\S*)"
    matches = re.finditer(pattern, value)
    result = {match[1]: match[2] for match in matches}
    return result


def parse_request_line(line: str) -> Tuple[ProtoMethod, str]:
    split = line.split(" ", 1)
    if len(split) != 2:
        raise ParseError("Invalid request line")
    (method, url) = split
    if not ProtoMethod.is_valid(method):
        raise ParseError("Unknown method")
    return (ProtoMethod[method], url)


def parse_response_line(line: str) -> Tuple[str, str]:
    split = line.split(" ", 1)
    if len(split) != 2:
        raise ParseError("Invalid status line")
    (status_code, status) = split
    if not ProtoStatusCode.is_valid(status_code):
        raise ParseError("Invalid status code")
    return (int(status_code), status.strip())
