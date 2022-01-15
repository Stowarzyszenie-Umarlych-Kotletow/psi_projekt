    # STRUCTS
from abc import abstractmethod

from common.config import *
from udp.structs import MessageType, HereStruct, HelloStruct, HeaderStruct, FileDataStruct, \
    InvalidHeaderException, Struct


class Datagram:
    def __init__(self, message_type: MessageType):
        self._header: HeaderStruct = HeaderStruct(message_type)
        self._message = None

    def get_header(self) -> HeaderStruct:
        return self._header

    @abstractmethod
    def get_message(self):
        pass

    def get_message_type(self) -> MessageType:
        return self._header.get_message_type()

    @staticmethod
    def msg_type_to_datagram(message_type):
        if message_type == MessageType.HELLO:
            return HelloDatagram
        if message_type == MessageType.HERE:
            return HereDatagram
        if message_type == MessageType.FIND:
            return FindDatagram
        if message_type == MessageType.FOUND:
            return FoundDatagram
        if message_type == MessageType.NOTFOUND:
            return NotFoundDatagram

    @staticmethod
    def _msg_type_from_datagram_bytes(datagram_bytes):
        header = HeaderStruct.from_bytes(datagram_bytes)
        message_type = header.get_message_type()
        return message_type

    @classmethod
    def from_bytes(cls, datagram_bytes: bytes):
        """
        :param datagram_bytes: datagram bytes received from udp socket
        :return:
        - None if message_type does not match
        - SomeDatagram (cls) instance if datagram type matches message type
        """

        try:
            message_type = cls._msg_type_from_datagram_bytes(datagram_bytes)
            if cls.msg_type_to_datagram(message_type) != cls:
                raise InvalidHeaderException(f"Message id {message_type} does not match cls {cls}")
        except InvalidHeaderException as err:
            # if DEBUG:
            #     print(err)
            return None

        # shift datagram_bytes by header size to message_bytes
        message_bytes = HeaderStruct.shift_bytes_by_struct_size(datagram_bytes)

        # rebuild Datagram from message_bytes
        message_struct_cls = Struct.msg_type_to_struct(message_type)
        message_struct = message_struct_cls.from_bytes(message_bytes)
        return cls(message_struct)

    def to_bytes(self) -> bytes:
        header_bytes = self.get_header().to_bytes()
        message_bytes = self.get_message().to_bytes()
        return header_bytes + message_bytes


class HelloDatagram(Datagram):
    def __init__(self, hello_struct: HelloStruct = HelloStruct()):
        super().__init__(MessageType.HELLO)
        self._message: HelloStruct = hello_struct

    def get_message(self) -> HelloStruct:
        return self._message


class HereDatagram(Datagram):
    def __init__(self, here_struct: HereStruct = HereStruct()):
        super().__init__(MessageType.HERE)
        self._message: HereStruct = here_struct

    def get_message(self) -> HereStruct:
        return self._message


class FindDatagram(Datagram):
    def __init__(self, find_struct: FileDataStruct):
        super().__init__(MessageType.FIND)
        self._message: FileDataStruct = find_struct

    def get_message(self) -> FileDataStruct:
        return self._message


class FoundDatagram(Datagram):
    def __init__(self, found_struct: FileDataStruct):
        super().__init__(MessageType.FOUND)
        self._message: FileDataStruct = found_struct

    def get_message(self) -> FileDataStruct:
        return self._message


class NotFoundDatagram(Datagram):
    def __init__(self, notfound_struct: FileDataStruct):
        super().__init__(MessageType.NOTFOUND)
        self._message: FileDataStruct = notfound_struct

    def get_message(self) -> FileDataStruct:
        return self._message
