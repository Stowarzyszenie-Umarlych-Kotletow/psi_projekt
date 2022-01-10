import socket
import sys
import ipaddress

PORT = 12345
BUFFER_SIZE = 128

if len(sys.argv) != 2:
    self_exec = sys.argv[0] if len(sys.argv) > 0 else "./server.py"
    print(f"Usage: {self_exec} [bind IP address]\n")
    exit(1)

ip_addr = sys.argv[1]

try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
        server_socket.bind((ip_addr, PORT))
        print(f"Receiving datagrams on {ip_addr}:{PORT}...")
        while True:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            num_bytes = len(data)
            data = data.decode(encoding="utf-8")  # convert from bytes to string
            print(f"Received {num_bytes} bytes from {addr}: {data}")

except socket.error as e:
    sys.stderr.write(f"[ERROR] Socket failed: {e.strerror}\n")
    exit(1)
