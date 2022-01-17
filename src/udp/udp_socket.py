import asyncio
import queue
import socket
import sys
from asyncio import Future
from threading import Thread
from typing import Tuple, Callable

from common.config import *
from common.tasks import new_loop
from common.utils import all_ip4_addresses


class AsyncioDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, receive_callbacks):
        self._receive_callbacks = receive_callbacks
        self.transport = None
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, address):
        if BROADCAST_OMIT_SELF:
            # drop broadcasts coming from us
            if address[0] in all_ip4_addresses():
                return

        for callback in self._receive_callbacks:
            callback(data, address)


class UdpSocket:
    def __init__(
            self,
            address: Tuple[str, int] = (UNICAST_IP, UNICAST_PORT),
            buffer_size: int = UDP_BUFFER_SIZE,
    ):
        self._server_task = None
        self._buffer_size = buffer_size
        self._address = address
        self._socket = None
        self._send_queue = queue.Queue()
        self._receive_callbacks = []
        self._loop: asyncio.AbstractEventLoop = None
        self._transport = None

    def start(self):
        self._init_socket()
        self._socket.bind(self._address)
        self._loop = new_loop()
        self._server_task: Future = asyncio.run_coroutine_threadsafe(
            self._serve_udp(), self._loop
        )

    async def _serve_udp(self):
        self._transport, protocol = await self._loop.create_datagram_endpoint(
            lambda: AsyncioDatagramProtocol(
                receive_callbacks=self._receive_callbacks
            ),
            sock=self._socket
        )
        self._loop.run_forever()

    def stop(self):
        self._transport.close()
        self._socket.close()
        del self._socket
        self._loop.stop()

    def add_receive_callback(self, callback: Callable[[bytes, Tuple[str, int]], None]):
        self._receive_callbacks.append(callback)

    def send(self, data: bytes):
        """queries send method"""
        self.send_to(data, self._address[0], self._address[1])

    def send_to(self, data: bytes, ip_address: str, port: int = None):
        """queries send_to method"""
        if port is None:
            port = self._address[1]
        if ip_address is None or port is None:
            raise ValueError("Destination port or ip is not specified")
        try:
            self._socket.sendto(data, (ip_address, port))

        except Exception as err:
            print("[!] Error sending packet: %s" % err)
            sys.exit(1)

    def _init_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class BroadcastSocket(UdpSocket):
    def __init__(self, address=(BROADCAST_IP, BROADCAST_PORT), buffer_size=UDP_BUFFER_SIZE):
        super().__init__(address, buffer_size)

    def _init_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
