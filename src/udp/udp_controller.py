import copy
import datetime
import threading
import time

from udp.datagrams import HelloDatagram, HereDatagram, FindDatagram, FoundDatagram, NotFoundDatagram
from udp.found_response import FoundResponse
from udp.structs import FileDataStruct
from udp.udp_socket import *
from common.utils import sha256sum


class InvalidSearchArgsException(Exception):
    """Raised when find args are not vaild"""

    def __init__(self, message="Search args are not vaild"):
        super().__init__(message)


class UdpController:
    def __init__(self):
        self._broadcast_socket = BroadcastSocket()
        self._unicast_socket = UdpSocket()
        self._add_receive_callbacks()

        self._t_broadcast_alive = Thread(target=self._alive_agent, daemon=True)

        # variables starting with __ are not thread safe
        self.__known_peers = dict()
        self._known_peers_lock = threading.Lock()

        # todo obtain this from filesystem_controller
        self.__files = dict()
        self._files_lock = threading.Lock()

        # search phrase that tells you what is currently being searched for (only filename)
        # (if not None, then it means we are collecting found/not found responses)
        self.__search_target = None

        # peers that not yet responded to find
        self.__peers_not_responded = set()

        # dict of keys (file_hash, provider_ip) and of values FoundResponse
        self.__found_responses = dict()

        # common lock for searching, found_responses and peers_not_responded
        self._search_lock = threading.Lock()

    def _add_receive_callbacks(self):
        """pass callback functions down to receiver"""
        self._broadcast_socket.add_receive_callback(self.find_callback)
        self._broadcast_socket.add_receive_callback(self.hello_callback)
        self._broadcast_socket.add_receive_callback(self.here_callback)
        self._unicast_socket.add_receive_callback(self.found_callback)
        self._unicast_socket.add_receive_callback(self.not_found_callback)

    def start(self):
        # start threads
        self._t_broadcast_alive.start()

        # start sockets (and their threads)
        self._broadcast_socket.start()
        self._unicast_socket.start()

        # broadcast hello message
        self._broadcast_socket.send(HelloDatagram().to_bytes())

        # EXAMPLE todo delete
        some_random_sha = sha256sum("asdfawfawf")  # SHA Is hash of file + name
        some_random_sha2 = sha256sum("asdfaw2fawf")
        self._files_lock.acquire()
        self.__files[some_random_sha] = {
            'hash': some_random_sha,
            'name': "kody_gta.txt",
            'path': "/home/alojzybulka/kody_gta.txt",
            'last_checked': datetime.datetime.now()
        }
        self.__files[some_random_sha2] = {
            'hash': some_random_sha2,
            'name': "nuclear_keys.txt",
            'path': "/home/alojzybulka/tajne/nuclear_keys.txt",
            'last_checked': datetime.datetime.now()
        }
        self._files_lock.release()

    def stop(self):
        # TODO
        pass

    def get_peers(self):
        self._known_peers_lock.acquire()
        known_peers_copy = copy.deepcopy(self.__known_peers)
        self._known_peers_lock.release()
        return known_peers_copy

    def get_peer(self, ip):
        return self.get_peers().get(ip)

    def search(self, file_name: str = None, file_hash: str = None) -> dict:
        if not file_name:
            raise InvalidSearchArgsException("Filename cannot be empty")

        if file_hash is None:
            file_hash = ""

        if file_hash != "" and len(file_hash) != 64:  # todo verify if it is legit sha256
            raise InvalidSearchArgsException("File hash does not look like sha256sum")

        self._search_lock.acquire()
        self.__search_target = (file_name, file_hash)
        self.__found_responses = dict()
        self.__peers_not_responded = set(self.get_peers().keys())
        self._search_lock.release()

        find_struct = FileDataStruct(file_name, file_hash)
        find_datagram = FindDatagram(find_struct)

        self._broadcast_socket.send(find_datagram.to_bytes())

        # find and found callbacks are now working
        time.sleep(FINDING_TIME)

        # check if all known peers responded and retry if not
        for retry in range(FINDING_RETRIES):
            if len(self.__peers_not_responded) != 0:
                self._broadcast_socket.send(find_datagram.to_bytes())
                time.sleep(FINDING_TIME)

        # delete peers that did not respond
        self._known_peers_lock.acquire()
        for peer_ip in self.__peers_not_responded:
            self.__known_peers.pop(peer_ip)
        self._known_peers_lock.release()

        # disable finding mode
        self._search_lock.acquire()
        self.__search_target = None
        self._search_lock.release()

        return self.__found_responses

    # UDP BROADCAST RECEIVE CALLBACKS

    def hello_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_hello_datagram = HelloDatagram.from_bytes(datagram_bytes)
        if received_hello_datagram is not None:
            if DEBUG:
                print(f"Recieved hello datagram from {address[0]}:{address[1]}")
            here_datagram = HereDatagram()
            self._broadcast_socket.send(here_datagram.to_bytes())

    def here_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_here_datagram = HereDatagram.from_bytes(datagram_bytes)

        if received_here_datagram is not None:
            message = received_here_datagram.get_message()
            if DEBUG:
                print(f"Recieved here datagram from {address[0]}:{address[1]}")
            self._known_peers_lock.acquire()
            self.__known_peers[address[0]] = {
                'ip': address[0],
                'last_updated': datetime.datetime.now(),
                'tcp_port': message.get_tcp_port(),
                'unicast_port': message.get_unicast_port()
            }
            self._known_peers_lock.release()

    def find_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FindDatagram
        received_find_datagram = FindDatagram.from_bytes(datagram_bytes)
        if received_find_datagram is None:
            return

        # check if peer is known
        ip_address = address[0]
        peer = self.get_peer(ip_address)
        if peer is None:
            return

        if DEBUG:
            print(f"Recieved find datagram from {address[0]}:{address[1]}")
        # todo check if file exists in local library
        response_found_datagram = FoundDatagram(received_find_datagram.get_message())

        unicast_port = peer['unicast_port']
        self._unicast_socket.send_to(response_found_datagram.to_bytes(), ip_address, unicast_port)

    def get_search_target(self):
        self._search_lock.acquire()
        search_target = copy.deepcopy(self.__search_target)
        self._search_lock.release()
        return search_target

    # UDP UNICAST RECEIVE CALLBACKS

    def found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if finding is active
        if self.get_search_target() is None:
            return

        # check if datagram is of type FoundDatagram
        received_found_datagram = FoundDatagram.from_bytes(datagram_bytes)
        if received_found_datagram is None:
            return

        # todo check if found response matches _finding (file hash and file name)

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.get_peers():
            return

        # create find_response
        find_response = FoundResponse(received_found_datagram.get_message(), provider_ip)

        # add provider to the set
        self._search_lock.acquire()
        if provider_ip in self.__peers_not_responded:
            self.__peers_not_responded.remove(provider_ip)
        self.__found_responses[(find_response.get_hash(), find_response.get_name())] = find_response
        self._search_lock.release()

    def not_found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if finding is active
        if self.__search_target is None:
            return

        # check if datagram is of type FoundDatagram
        received_not_found_datagram = NotFoundDatagram.from_bytes(datagram_bytes)
        if received_not_found_datagram is None:
            return

        # todo check if found response matches _finding (file hash and file name) (may be not necessary in not_found)

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.get_peers():
            return

        # add provider to the set
        self._search_lock.acquire()
        if provider_ip in self.__peers_not_responded:
            self.__peers_not_responded.remove(provider_ip)
        self._search_lock.release()

    def _alive_agent(self):
        """
        thread target:
        agent that broadcasts HERE messages every 10 seconds
        and deletes peers older than 30 seconds
        """
        here_bytes = HereDatagram().to_bytes()

        while True:
            self._broadcast_socket.send(here_bytes)
            self._delete_old_peers()
            # todo check if the files are still in the filesystem
            time.sleep(10)

    def _delete_old_peers(self):
        """
        deletes peers older than 30 seconds
        """
        now = datetime.datetime.now()
        self._known_peers_lock.acquire()
        peers = self.__known_peers
        for peer_ip in list(peers.keys()):
            diff = now - peers[peer_ip]['last_updated']
            if diff.total_seconds() > 30:
                peers.pop(peer_ip)  # delete peer from the list
        self._known_peers_lock.release()
