import datetime

# todo add type hinting for last_updated


class Peer:
    def __init__(self, ip_address: str, tcp_port: int, unicast_port: int, last_updated):
        self._ip_address = ip_address
        self._tcp_port = tcp_port
        self._unicast_port = unicast_port
        self._last_updated = last_updated

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def tcp_port(self):
        return self._tcp_port

    @property
    def unicast_port(self):
        return self._unicast_port

    @property
    def last_updated(self):
        return self._last_updated

    @last_updated.setter
    def last_updated(self, date):
        self._last_updated = date
