from typing import Optional

from common.config import MAX_FILENAME_LENGTH


class LogicError(Exception):
    def __init__(self, msg: Optional[str] = None, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.msg}"


class FileDuplicateException(Exception):
    def __init__(self, msg: Optional[str] = None, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg


class UnsupportedError(LogicError):
    pass


class ParseError(LogicError):
    pass


class FileNameTooLongException(LogicError):
    pass
