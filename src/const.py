# Unicast and broadcast ports are the same in the whole network
# BROADCAST_IP must be set the same in the whole network
# if you experience problems with

# Config
BROADCAST_PORT = 12345
UNICAST_PORT = 12346
TCP_PORT = 12347
#BROADCAST_IP = '<broadcast>'  # default
BROADCAST_IP = '192.168.1.255'
UNICAST_IP = '0.0.0.0'
FINDING_TIME = 2
FINDING_RETRIES = 2

# Development
DEBUG = False
BROADCAST_OMIT_SELF = True
PROTO_VERSION = 1
ENCODING = 'utf-8'
MAGIC_NUMBER = 0xd16d
UDP_BUFFER_SIZE = 1024
MAX_FILENAME_LENGTH = 31
MAX_RSP_ID_SIZE = 5 # response id max size
PEER_FP_SHORT = 16 
FILE_FP_HR_LEN = 13 # file fingerprint header length
MAX_STATUS_MSG_SIZE = 33
MAX_PROGRESS_MSG_LEN = 8
TABLE_SEP_LEN = 2
SEARCH_HR_LEN = 77
STATUS_HR_LEN = 102