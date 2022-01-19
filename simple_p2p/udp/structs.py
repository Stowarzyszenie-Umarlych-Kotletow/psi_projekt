import struct
from abc import abstractmethod

from simple_p2p.common.config import *
from simple_p2p.udp.message_type import MessageType


class InvalidHeaderException(Exception):
    """Raised when proto/magick number/message_id does not match"""

    def __init__(self, message="Header is not valid"):
        super().__init__(message)


class Struct:
    FORMAT = None

    def __init__(self, *args):
        pass

    @abstractmethod
    def to_bytes(self):
        pass

    @classmethod
    @property
    def format(cls):
        return cls.FORMAT

    @classmethod
    @property
    def struct_size(cls):
        return struct.calcsize(cls.FORMAT)

    @classmethod
    def shift_bytes_by_struct_size(cls, struct_bytes):
        return struct_bytes[cls.struct_size:]

    @classmethod
    def from_bytes(cls, struct_bytes):
        """
        returns class created from retrieved struct
        """
        cut_bytes = struct_bytes[0:cls.struct_size]
        unpacked = struct.unpack(cls.FORMAT, cut_bytes)
        return cls(*unpacked)

    @staticmethod
    def msg_type_to_struct(message_type):
        if message_type == MessageType.HELLO:
            return HelloStruct
        if message_type == MessageType.HERE:
            return HereStruct
        if message_type == MessageType.FIND:
            return FileDataStruct
        if message_type == MessageType.FOUND:
            return FileDataStruct
        if message_type == MessageType.NOTFOUND:
            return FileDataStruct


class HeaderStruct(Struct):
    FORMAT = "!HBB"

    def __init__(self, message_id: int, proto_version: int = PROTO_VERSION, magic_number: int = MAGIC_NUMBER):
        super().__init__()
        self._message_id: int = message_id
        self._proto_version: int = proto_version
        self._magic_number: int = magic_number

    @property
    def proto_version(self) -> int:
        return self._proto_version

    @property
    def magic_number(self) -> int:
        return self._magic_number

    @property
    def message_id(self) -> int:
        return self._message_id

    @property
    def message_type(self) -> MessageType:
        return MessageType(self._message_id)

    def to_bytes(self) -> bytes:
        return struct.pack(self.FORMAT, self._magic_number, self._proto_version, self._message_id)

    @classmethod
    def from_bytes(cls, struct_bytes):
        """
        we must overload that method,
        because the arguments are in the different order than struct data
        """
        cut_bytes = struct_bytes[0:cls.struct_size]
        magick_number, proto_version, message_id = struct.unpack(cls.FORMAT, cut_bytes)

        if magick_number != MAGIC_NUMBER:
            raise InvalidHeaderException("Unknown magic number")
        if proto_version != PROTO_VERSION:
            raise InvalidHeaderException("Invalid protocol")
        if message_id not in set(message_type.value for message_type in MessageType):
            raise InvalidHeaderException("Unknown message type")

        return cls(message_id, proto_version, magick_number)


class HelloStruct(Struct):
    FORMAT = "!"

    def __init__(self):
        super().__init__()

    def to_bytes(self) -> bytes:
        return struct.pack(self.FORMAT)


class HereStruct(Struct):
    FORMAT = "!HH"

    def __init__(self, unicast_port: int, tcp_port: int):
        super().__init__()
        self._unicast_port = unicast_port
        self._tcp_port = tcp_port

    @property
    def tcp_port(self) -> int:
        return self._tcp_port

    @property
    def unicast_port(self) -> int:
        return self._unicast_port

    def to_bytes(self) -> bytes:
        return struct.pack(self.FORMAT, self._unicast_port, self._tcp_port)


class FileDataStruct(Struct):
    FORMAT = f"!{str(MAX_FILENAME_LENGTH + 1)}p64sQ"  # first byte of name contains size of string

    def __init__(self, file_name, file_hash, file_size: int = 0):
        super().__init__()
        if type(file_name) == str:
            file_name = bytes(file_name, ENCODING)
        if type(file_hash) == str:
            file_hash = bytes(file_hash, ENCODING)
        if type(file_name) != bytes or type(file_hash) != bytes:
            raise TypeError("Invalid file_name or file_hash type")
        self._file_name: bytes = file_name
        self._file_hash: bytes = file_hash
        self._file_size: int = file_size

    @property
    def file_digest_encoded(self) -> bytes:
        return self._file_hash

    @property
    def file_name_encoded(self) -> bytes:
        return self._file_name

    @property
    def file_digest(self) -> str:
        if self.digest_is_empty:
            return ""  # TODO: BRO PLS FIX ME
        return str(self._file_hash, ENCODING)

    @property
    def file_name(self) -> str:
        return str(self._file_name, ENCODING)

    @property
    def digest_is_empty(self):
        return self.file_digest_encoded[0] == 0

    @property
    def file_size(self):
        return self._file_size

    @property
    def name_is_empty(self):
        return len(self.file_name) == 0

    def to_bytes(self):
        return struct.pack(self.FORMAT, self._file_name, self._file_hash, self._file_size)
