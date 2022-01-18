import asyncio
import logging
import queue
import random
import socket
import sys
from asyncio import AbstractEventLoop, Future
from typing import Tuple, Callable

from common.config import *
from common.tasks import new_loop
from common.utils import all_ip4_addresses


class AsyncioDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, receive_callbacks, broadcast_mode=False):
        self._logger = logging.getLogger("AsyncioDatagramProtocol")
        self._receive_callbacks = receive_callbacks
        self._broadcast_mode = broadcast_mode
        self._drop_counter = 0
        self.transport = None
        super().__init__()

    @property
    def broadcast_mode(self):
        return self._broadcast_mode

    @broadcast_mode.setter
    def broadcast_mode(self, set_to):
        self._broadcast_mode = set_to

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, address):
        if BROADCAST_OMIT_SELF:
            # drop broadcasts coming from us
            if address[0] in all_ip4_addresses():
                return

        # drop broadcast by chance
        if self._broadcast_mode:
            if self._drop_counter == 0:
                drop_broadcast = random.random() * 100 <= Config().broadcast_drop_chance
                if drop_broadcast:
                    self._drop_counter = Config().broadcast_drop_in_row
            if self._drop_counter != 0:
                no = Config().broadcast_drop_in_row - self._drop_counter + 1
                self._logger.debug(
                    "Dropping incoming broadcast datagram (%s/%s)",
                    no,
                    Config().broadcast_drop_in_row,
                )
                self._drop_counter -= 1
                return

        # run callbacks
        for callback in self._receive_callbacks:
            try:
                callback(data, address)
            except Exception as exc:
                self._logger.error("Error while executing UDP callback", exc_info=exc)


class UdpSocket:
    def __init__(
        self,
        address: Tuple[str, int],
        buffer_size: int = UDP_BUFFER_SIZE,
    ):
        self._logger = logging.getLogger("UdpSocket")
        self._buffer_size = buffer_size
        self._address = address
        self._socket = None
        self._send_queue = queue.Queue()
        self._receive_callbacks = []
        self._transport = None
        self._broadcast_mode = False

    def start(self, loop: AbstractEventLoop):
        self._init_socket()
        self._socket.bind(self._address)
        self._transport, protocol = asyncio.run_coroutine_threadsafe(
            self._create_udp(), loop
        ).result()

    async def _create_udp(self):
        return await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: AsyncioDatagramProtocol(
                receive_callbacks=list(self._receive_callbacks),
                broadcast_mode=self._broadcast_mode,
            ),
            sock=self._socket,
        )

    def stop(self):
        self._transport.close()
        self._socket.close()
        del self._socket
        self._socket = None

    def add_receive_callback(self, callback: Callable[[bytes, Tuple[str, int]], None]):
        if self._socket:
            raise LogicError("Cannot add callbacks while the socket is running")
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
        
        self._socket.sendto(data, (ip_address, port))



    def _init_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


class BroadcastSocket(UdpSocket):
    def __init__(self, address, buffer_size=UDP_BUFFER_SIZE):
        super().__init__(address, buffer_size)
        self._broadcast_mode = True

    def _init_socket(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
