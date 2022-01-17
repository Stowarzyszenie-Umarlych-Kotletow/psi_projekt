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

# Development
BROADCAST_OMIT_SELF = True
PROTO_VERSION = 1
ENCODING = 'utf-8'
MAGIC_NUMBER = 0xd16d
UDP_BUFFER_SIZE = 2048
MAX_FILENAME_LENGTH = 27
MOCK_CONTROLLER_PATH = os.getcwd()
DIGEST_ALG = 'sha256'
FINGERPRINT_LENGTH = 10
FINDING_TIME = 2
SEARCH_RETRIES = 2
BROADCAST_DROP_CHANCE = 50  # chance of dropping broadcast datagram in %
BROADCAST_DROP_IN_ROW = 3  # number of broadcast datagrams dropped in a row
