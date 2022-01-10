import time
from threading import ThreadError

from src.udp.udp_socket import *


class Controller:
    def __init__(self):
        self.broadcast_socket = BroadcastSocket()
        self.broadcast_socket.add_receive_callback(self.hello_udp_controller_callback)
        self.unicast_socket = UdpSocket()

        try:
            self._t_broadcast_alive = Thread(target=self._broadcast_alive, daemon=True)

        except ThreadError as err:
            print("[!] Error sending packet: %s" % err)
            sys.exit(1)

    def start(self):
        self._t_broadcast_alive.start()
        self.broadcast_socket.start()
        self.unicast_socket.start()
        self.broadcast_socket.send('HELLO')
        self.broadcast_socket.send('FIND')

    def stop(self):
        pass

    def hello_udp_controller_callback(self, data_str: str, address: Tuple[str, int]):
        if data_str == 'HELLO':
            self.broadcast_socket.send('HERE PORT 1234 (ans)')

    def _broadcast_alive(self):
        while True:
            self.broadcast_socket.send('HERE PORT 1234')
            time.sleep(10)
