# STRUCTS
import struct
from abc import abstractmethod

from common.config import *
from udp.message_type import MessageType


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
    def get_format(cls):
        return cls.FORMAT

    @classmethod
    def get_struct_size(cls):
        return struct.calcsize(cls.FORMAT)

    @classmethod
    def shift_bytes_by_struct_size(cls, struct_bytes):
        return struct_bytes[cls.get_struct_size():]

    @classmethod
    def from_bytes(cls, struct_bytes):
        """
        returns class created from retrieved struct
        """
        cut_bytes = struct_bytes[0:cls.get_struct_size()]
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

    def get_proto_version(self) -> int:
        return self._proto_version

    def get_magic_number(self) -> int:
        return self._magic_number

    def get_message_id(self) -> int:
        return self._message_id

    def get_message_type(self) -> MessageType:
        return MessageType(self._message_id)

    def to_bytes(self) -> bytes:
        return struct.pack(self.FORMAT, self._magic_number, self._proto_version, self._message_id)

    @classmethod
    def from_bytes(cls, struct_bytes):
        """
        we must overload that method,
        because the arguments are in the different order than struct data
        """
        cut_bytes = struct_bytes[0:cls.get_struct_size()]
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

    def to_bytes(self):
        return struct.pack(self.FORMAT)


class HereStruct(Struct):
    FORMAT = "!HH"

    def __init__(self, unicast_port: int = UNICAST_PORT, tcp_port: int = TCP_PORT):
        super().__init__()
        self._unicast_port = unicast_port
        self._tcp_port = tcp_port

    def get_tcp_port(self):
        return self._tcp_port

    def get_unicast_port(self):
        return self._unicast_port

    def to_bytes(self):
        return struct.pack(self.FORMAT, self._unicast_port, self._tcp_port)


class FileDataStruct(Struct):
    FORMAT = f"!{str(MAX_FILENAME_LENGTH + 1)}p64s"  # first byte of name contains size of string

    def __init__(self, file_name, file_hash):
        super().__init__()
        if type(file_name) == str:
            file_name = bytes(file_name, ENCODING)
        if type(file_hash) == str:
            file_hash = bytes(file_hash, ENCODING)
        if type(file_name) != bytes or type(file_hash) != bytes:
            raise TypeError("Invalid file_name or file_hash type")
        self._file_name: bytes = file_name
        self._file_hash: bytes = file_hash

    def get_file_hash_encoded(self) -> bytes:
        return self._file_hash

    def get_file_name_encoded(self) -> bytes:
        return self._file_name

    def get_file_hash(self) -> str:
        return str(self._file_hash, ENCODING)

    def get_file_name(self) -> str:
        return str(self._file_name, ENCODING)

    def hash_is_empty(self):
        return self.get_file_hash_encoded()[0] == 0

    def name_is_empty(self):
        return len(self.get_file_name()) == 0

    def to_bytes(self):
        return struct.pack(self.FORMAT, self._file_name, self._file_hash)