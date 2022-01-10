import socket
import sys
import ipaddress

PORT = 12345
BUFFER_SIZE = 128


try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        print(f"Receiving datagrams on ?:0...")
        server_socket.bind(('', 12347))
        while True:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            num_bytes = len(data)
            data = data.decode(encoding="utf-8")  # convert from bytes to string
            print(f"Received {num_bytes} bytes from {addr}: {data}")

except socket.error as e:
    sys.stderr.write(f"[ERROR] Socket failed: {e.strerror}\n")
    exit(1)
