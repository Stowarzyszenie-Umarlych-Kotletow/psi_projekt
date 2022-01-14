class ProtoError(Exception):
    def __init__(self, code: "ProtoStatusCode", fatal=True, *args: object) -> None:
        super().__init__(*args)
        self.code = code
        self.fatal = fatal


class InvalidResponseError(RuntimeError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class InvalidRequestError(RuntimeError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class MessageError(Exception):
    def __init__(self, msg: str, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return f"{self.msg}"


class InvalidRangeError(MessageError):
    pass


class UnsupportedError(MessageError):
    pass


class ParseError(MessageError):
    pass
