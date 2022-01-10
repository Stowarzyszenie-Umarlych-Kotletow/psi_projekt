import socket
import sys


def broadcast(data_str, port):
    data = data_str.encode(encoding="utf-8")
    try:
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # broadcast_socket.bind(('', 12345))
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except Exception as err:
        print("[!] Error creating broadcast socket: %s" % err)
        sys.exit(1)
    try:
        broadcast_socket.sendto(data, ('<broadcast>', port))

    except Exception as err:
        print("[!] Error sending packet: %s" % err)
        sys.exit(1)
