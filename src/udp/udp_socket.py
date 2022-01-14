import queue
import socket
import sys
from threading import Thread
from typing import Tuple, Callable

from common.utils import all_ip4_addresses
from common.config import *


class UdpSocket:
    def __init__(self, address: Tuple[str, int] = (UNICAST_IP, UNICAST_PORT), buffer_size: int = UDP_BUFFER_SIZE):
        self._buffer_size = buffer_size
        self._address = address
        self._socket = None
        self._init_socket()
        self._send_queue = queue.Queue()
        self._t_queue_popper = Thread(target=self._q_popper, daemon=True)
        self._t_listener = Thread(target=self._listen, daemon=True)
        self._receive_callbacks = []

    def __del__(self):
        self._socket.close()

    def start(self, timeout=None):
        self._t_queue_popper.start()
        self._t_listener.start()

    def stop(self):
        pass

    def add_receive_callback(self, callback: Callable[[bytes, Tuple[str, int]], None]):
        self._receive_callbacks.append(callback)

    def send(self, data: bytes):
        """queries send method"""
        self.send_to(data, self._address[0], self._address[1])

    def send_to(self, data: bytes, ip_address: str, port: int = None):
        """queries send_to method"""
        self._send_queue.put((data, ip_address, port))

    def _init_socket(self):
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.bind(self._address)
            if DEBUG:
                print(f"Initialized UDP listener on {self._address[0]}:{self._address[1]}")

        except socket.error as e:
            sys.stderr.write(f"[ERROR] Socket failed: {e.strerror}\n")
            exit(1)

    def _receive(self):
        data, address = self._socket.recvfrom(self._buffer_size)
        if BROADCAST_OMIT_SELF:
            # drop broadcasts coming from us
            if address[0] in all_ip4_addresses():
                return self._receive()
        num_bytes = len(data)
        if DEBUG:
            print(f"Received {num_bytes} bytes from {address}: {data}")

        for callback in self._receive_callbacks:
            callback(data, address)

    def _listen(self):
        while True:
            self._receive()

    def _q_popper(self):
        while True:
            data, ip_address, port = self._send_queue.get(block=True)
            self._send_to(data, ip_address, port)
            self._send_queue.task_done()

    def _send(self, data: bytes):
        self._send_to(data, self._address[0], self._address[1])

    def _send_to(self, data: bytes, ip_address: str, port: int = None):
        if port is None:
            port = self._address[1]
        if ip_address is None or port is None:
            raise ValueError("Destination port or ip is not specified")
        try:
            self._socket.sendto(data, (ip_address, port))

        except Exception as err:
            print("[!] Error sending packet: %s" % err)
            sys.exit(1)


class BroadcastSocket(UdpSocket):
    def __init__(self, address=(BROADCAST_IP, BROADCAST_PORT), buffer_size=UDP_BUFFER_SIZE):
        super().__init__(address, buffer_size)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
