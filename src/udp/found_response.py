from udp.structs import FileDataStruct


class FoundResponse:  # todo maybe move this somewhere else
    def __init__(self, found_struct: FileDataStruct, provider_ip, is_found: bool):
        self._found_struct = found_struct
        self._provider_ip = provider_ip
        self._is_found = is_found

    @property
    def is_found(self):
        return self._is_found

    @property
    def provider_ip(self):
        return self._provider_ip

    @property
    def found_struct(self):
        return self._found_struct

    @property
    def digest(self):
        return self.found_struct.file_digest

    @property
    def name(self):
        return self.found_struct.file_name
