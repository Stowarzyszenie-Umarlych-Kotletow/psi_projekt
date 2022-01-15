from udp.udp_controller import UdpController


class Controller:
    def __init__(self):
        self._udp_controller = UdpController()

    def start(self):
        self._udp_controller.start()

    def stop(self):
        self._udp_controller.stop()

    def get_peers(self):
        return self._udp_controller.get_peers()

    def search_file(self, file_name: str = None, file_hash: str = None) -> dict:
        return self._udp_controller.search(file_name, file_hash)
