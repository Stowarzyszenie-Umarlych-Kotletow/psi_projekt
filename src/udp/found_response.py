from udp.structs import FileDataStruct


class FoundResponse:  # todo maybe move this somewhere else
    def __init__(self, found_struct: FileDataStruct, provider_ip):
        self._found_struct = found_struct
        self._provider_ip = provider_ip

    def get_provider_ip(self):
        return self._provider_ip

    def get_found_struct(self):
        return self._found_struct

    def get_hash(self):
        return self.get_found_struct().get_file_hash()

    def get_name(self):
        return self.get_found_struct().get_file_name()