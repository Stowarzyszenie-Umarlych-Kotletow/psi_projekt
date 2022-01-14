from enum import IntEnum


class MessageType(IntEnum):
    HELLO = 0x01
    HERE = 0x02
    FIND = 0x11
    FOUND = 0x12
    NOTFOUND = 0x13
