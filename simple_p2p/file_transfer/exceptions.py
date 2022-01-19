from typing import Optional

from simple_p2p.common.exceptions import LogicError


class ProtoError(Exception):
    def __init__(self, code: "ProtoStatusCode", fatal=True, *args: object) -> None:
        super().__init__(*args)
        self.code = code
        self.fatal = fatal


class InvalidRangeError(LogicError):
    pass

class InconsistentFileStateError(LogicError):
    pass