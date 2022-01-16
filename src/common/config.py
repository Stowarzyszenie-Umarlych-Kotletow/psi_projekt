import os
# Unicast and broadcast ports are the same in the whole network
# BROADCAST_IP must be set the same in the whole network
# if you experience problems with

# Config
BROADCAST_PORT = 12345
UNICAST_PORT = 12346
TCP_PORT = 13371
BROADCAST_IP = '<broadcast>'  # default
# BROADCAST_IP = '192.168.80.255'
UNICAST_IP = '0.0.0.0'
FINDING_TIME = 2
SEARCH_RETRIES = 2

# Development
DEBUG = True
BROADCAST_OMIT_SELF = True
PROTO_VERSION = 1
ENCODING = 'utf-8'
MAGIC_NUMBER = 0xd16d
UDP_BUFFER_SIZE = 1024
MAX_FILENAME_LENGTH = 31
MOCK_CONTROLLER_PATH = os.getcwd()
DIGEST_ALG = 'sha256'
FINGERPRINT_LENGTH = 10
