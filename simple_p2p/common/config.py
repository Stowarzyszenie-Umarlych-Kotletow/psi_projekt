from simple_p2p.common.exceptions import LogicError
from simple_p2p.common.models import Singleton

# Config

DEFAULT_BROADCAST_PORT = 13370
DEFAULT_UDP_PORT = 13371
DEFAULT_TCP_PORT = 13372
DEFAULT_BIND_IP = '0.0.0.0'

BROADCAST_OMIT_SELF = True
PROTO_VERSION = 1
ENCODING = "utf-8"
MAGIC_NUMBER = 0xD16D
FILE_CHUNK_SIZE = 16384
UDP_BUFFER_SIZE = 2048
UDP_PEER_CLEANUP_PERIOD = 30
UDP_ADVERTISE_PERIOD = 10
TCP_FILE_SEND_TIMEOUT = 15
TCP_FILE_RECEIVE_TIMEOUT = 10
MAX_FILENAME_LENGTH = 32
DIGEST_ALG = "sha256"
FINGERPRINT_LENGTH = 10
FINDING_TIME = 2
SEARCH_RETRIES = 2

METADATA_FOLDER_NAME = ".meta"
YAML_EXTENSION = ".yaml"

class Config(metaclass=Singleton):
    def __init__(self) -> None:
        self.broadcast_iface: str = "default"
        self.broadcast_port: int = DEFAULT_BROADCAST_PORT
        self.tcp_port: int = DEFAULT_TCP_PORT
        self.udp_port: int = DEFAULT_UDP_PORT
        self.bind_ip: str = DEFAULT_BIND_IP
        self.broadcast_drop_chance: int = 0
        self.broadcast_drop_in_row: int = 1

    def update(self, new_values: dict[str, object]):
        for (key, value) in new_values.items():
            if not hasattr(self, key):
                continue
            # ensure the variable type stays the same
            attr_type = type(getattr(self, key))
            try:
                casted_value = attr_type(value)
                setattr(self, key, casted_value)
            except ValueError:
                raise LogicError(
                    f"Error setting config property '{key}' of type '{attr_type.__name__}' to value '{value}'"
                )
