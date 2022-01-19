from simple_p2p.udp.structs import FileDataStruct


class FoundResponse:  # todo maybe move this somewhere else
    def __init__(self, found_struct: FileDataStruct, provider_ip, is_found: bool):
        self._found_struct = found_struct
        self._provider_ip = provider_ip
        self._is_found = is_found

    @property
    def is_found(self) -> bool:
        return self._is_found

    @property
    def provider_ip(self) -> str:
        return self._provider_ip

    @property
    def found_struct(self) -> FileDataStruct:
        return self._found_struct

    @property
    def digest(self) -> str:
        return self.found_struct.file_digest

    @property
    def name(self) -> str:
        return self.found_struct.file_name

    @property
    def file_size(self) -> int:
        return self.found_struct.file_size
