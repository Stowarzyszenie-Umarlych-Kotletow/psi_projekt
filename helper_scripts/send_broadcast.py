from broadcast_server import broadcast
from src.const import *

broadcast("broadcast message %s" % BROADCAST_PORT, BROADCAST_PORT)

