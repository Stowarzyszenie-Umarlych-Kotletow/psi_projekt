import asyncio
import copy
import datetime
import logging
import threading
import time
from typing import Dict, List

from file_transfer.exceptions import MessageError
from repository.file_metadata import FileMetadata

from udp.datagrams import HelloDatagram, HereDatagram, FindDatagram, FoundDatagram, NotFoundDatagram
from udp.found_response import FoundResponse
from udp.structs import FileDataStruct
from udp.udp_socket import *
from common.utils import sha256sum, is_sha256


class InvalidSearchArgsException(Exception):
    """Raised when find args are not valid"""

    def __init__(self, message="Search args are not valid"):
        super().__init__(message)


class UdpController:
    def __init__(self, controller):
        self._logger = logging.getLogger("UdpController")
        self._broadcast_socket = BroadcastSocket()
        self._unicast_socket = UdpSocket()
        self._controller = controller
        self._add_receive_callbacks()

        self._t_broadcast_alive = Thread(target=self._alive_agent, daemon=True)

        # variables starting with __ are not thread safe
        self.__known_peers = dict()
        self._known_peers_lock = threading.Lock()

        self._search_results: Dict[str, List[FoundResponse]] = {}

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
        self._broadcast_socket.send(HelloDatagram().to_bytes)
        self._logger.info("Started UDP controller")

    def stop(self):
        # TODO
        pass

    @property
    def known_peers(self):
        with self._known_peers_lock:
            known_peers_copy = copy.deepcopy(self.__known_peers)
            return known_peers_copy

    def get_peer_by_ip(self, ip):
        return self.known_peers.get(ip)

    async def search(self, file_name: str = None, file_digest: str = None) -> Dict[str, List[FoundResponse]]:
        if not file_name:
            raise InvalidSearchArgsException("Filename cannot be empty")

        if file_digest is None:
            file_digest = ""

        if file_digest != "" and not is_sha256(file_digest):
            raise InvalidSearchArgsException("File is not sha256sum")

        with self._search_lock:
            if file_name in self._search_results:
                self._logger.warning("Search | Attempted to search a file for which a search is already in progress")
                raise MessageError(f"There is another search for '{file_name}' in progress")
            self._search_results[file_name] = []

        peers_available = set(self.known_peers.keys())

        def get_missing_peers():
            peers_left = set(peers_available)
            with self._search_lock:
                for result in self._search_results[file_name]:
                    peers_left.remove(result.provider_ip)
            return peers_left

        find_struct = FileDataStruct(file_name, file_digest)
        find_datagram = FindDatagram(find_struct)
        self._broadcast_socket.send(find_datagram.to_bytes)

        # find and found callbacks are now working
        await asyncio.sleep(FINDING_TIME)

        # check if all known peers responded and retry if not
        missing_peers = get_missing_peers()
        for retry in range(SEARCH_RETRIES):
            if len(missing_peers) != 0:
                self._logger.info(
                    "Search | %s peers did not respond, retrying search for file %s with digest %s (%s/%s)",
                    len(missing_peers), file_name, file_digest, retry+1, SEARCH_RETRIES)
                with self._search_lock:
                    self._search_results[file_name].clear()
                self._broadcast_socket.send(find_datagram.to_bytes)
                await asyncio.sleep(FINDING_TIME)

        # delete peers that did not respond
        for peer_ip in missing_peers:
            self._logger.info("Search | Deleting unresponsive peer %s", peer_ip)
            self.remove_peer(peer_ip)

        # disable finding mode
        with self._search_lock:
            responses: List[FoundResponse] = self._search_results.pop(file_name)

        results_dict = dict()
        for response in responses:
            if response.is_found:
                results_dict.setdefault(response.digest, []).append(response)
        self._logger.info("Search | Found %s in %s out of %s peers", file_name,
                          sum(len(list) for list in results_dict.items()), len(peers_available))
        return results_dict

    # UDP BROADCAST RECEIVE CALLBACKS

    def hello_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_hello_datagram = HelloDatagram.from_bytes(datagram_bytes)
        if received_hello_datagram is None:
            return
        self._logger.debug("Hello | Discovering new peer %s", address[0])
        here_datagram = HereDatagram()
        self._broadcast_socket.send(here_datagram.to_bytes)

    def here_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_here_datagram = HereDatagram.from_bytes(datagram_bytes)

        if received_here_datagram is None:
            return
        message = received_here_datagram.message
        self._logger.debug("Here | Discovered peer %s with TCP port %s", address[0], address[1])

        with self._known_peers_lock:
            self.__known_peers[address[0]] = {
                'ip': address[0],
                'last_updated': datetime.datetime.now(),
                'tcp_port': message.tcp_port,
                'unicast_port': message.unicast_port
            }

    def find_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FindDatagram
        received_find_datagram = FindDatagram.from_bytes(datagram_bytes)
        if received_find_datagram is None:
            return
        find_struct = received_find_datagram.message

        # check if peer is known
        ip_address = address[0]
        peer = self.get_peer_by_ip(ip_address)
        if peer is None:
            return

        self._logger.debug("Find | Received datagram from %s", address[0])
        response_datagram = None
        try:
            file: FileMetadata = self._controller.get_file(find_struct.file_name)
            target_digest = find_struct.file_digest
            if target_digest and file.digest != target_digest:
                self._logger.warning("Find | Asked for file %s with digest %.8s, but local is %.8s", target_digest, file.digest)
                raise MessageError("Hash mismatch")
            response_datagram = FoundDatagram(FileDataStruct(file.name, file.digest, file.size))
            self._logger.debug("Find | Sending positive reply for file %s with digest %.8s", file.name, file.digest)
        except Exception as ex:
            response_datagram = NotFoundDatagram(find_struct)
            self._logger.debug("Find | Sending negative reply for file %s with digest %.8s", find_struct.file_name, find_struct.file_digest)
            pass
        
        unicast_port = peer['unicast_port']
        self._unicast_socket.send_to(response_datagram.to_bytes, ip_address, unicast_port)

    # UDP UNICAST RECEIVE CALLBACKS

    def found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FoundDatagram
        received_found_datagram = FoundDatagram.from_bytes(datagram_bytes)
        if received_found_datagram is None:
            return

        # todo check if found response matches _finding (file hash and file name)

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.known_peers:
            self._logger.warning("Found | Received from unknown peer %s", provider_ip)
            return

        # create find_response
        find_response = FoundResponse(received_found_datagram.message, provider_ip, True)

        # add provider to the set
        with self._search_lock:
            result_list = self._search_results.get(find_response.name)
            if result_list is not None:
                result_list.append(find_response)
        self._logger.debug("Found | Found file %s with digest %.8s, peer %s", find_response.name, find_response.digest, provider_ip)

    def not_found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FoundDatagram
        received_not_found_datagram = NotFoundDatagram.from_bytes(datagram_bytes)
        if received_not_found_datagram is None:
            return

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.known_peers:
            self._logger.warning("NotFound | Received from unknown peer %s", provider_ip)
            return

        # create find_response
        find_response = FoundResponse(received_not_found_datagram.message, provider_ip, False)

        # add provider to the set
        with self._search_lock:
            result_list = self._search_results.get(find_response.name)
            if result_list is not None:
                result_list.append(find_response)
        self._logger.debug("NotFound | Did not find file %s with digest %.8s, peer %s", provider_ip)

    def remove_peer(self, peer_ip):
        with self._known_peers_lock:
            return self.__known_peers.pop(peer_ip)

    def _alive_agent(self):
        """
        thread target:
        agent that broadcasts HERE messages every 10 seconds
        and deletes peers older than 30 seconds
        """
        here_bytes = HereDatagram().to_bytes

        while True:
            self._logger.debug("Broadcasting HERE message")
            self._broadcast_socket.send(here_bytes)
            self._delete_old_peers()
            # todo check if the files are still in the filesystem
            time.sleep(10)

    def _delete_old_peers(self):
        """
        deletes peers older than 30 seconds
        """
        now = datetime.datetime.now()
        with self._known_peers_lock:
            peers = self.__known_peers
            for peer_ip in list(peers.keys()):
                diff = now - peers[peer_ip]['last_updated']
                if diff.total_seconds() > 30:
                    self._logger.info("Removing peer %s because of inactivity", peer_ip)
                    peers.pop(peer_ip)  # delete peer from the list
