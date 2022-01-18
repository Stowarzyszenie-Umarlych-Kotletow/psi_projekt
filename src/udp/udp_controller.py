import asyncio
import copy
import datetime
import logging
import threading
import time
from typing import Dict, List, Tuple

from common.config import *
from common.tasks import coro_in_background, new_loop
from common.utils import get_ip4_broadcast, is_sha256
from common.exceptions import LogicError
from common.models import FileMetadata
from udp.datagrams import (
    HelloDatagram,
    HereDatagram,
    FindDatagram,
    FoundDatagram,
    NotFoundDatagram,
)
from udp.found_response import FoundResponse
from udp.structs import FileDataStruct, HereStruct
from udp.udp_socket import UdpSocket, BroadcastSocket
from udp.peer import Peer


class InvalidSearchArgsException(Exception):
    """Raised when find args are not valid"""

    def __init__(self, message="Search args are not valid"):
        super().__init__(message)


class UdpController:
    def __init__(self, controller):
        cfg = Config()

        self._logger = logging.getLogger("UdpController")
        broadcast_endpoint = (
            get_ip4_broadcast(cfg.broadcast_iface),
            cfg.broadcast_port,
        )
        self._broadcast_socket = BroadcastSocket(broadcast_endpoint)
        self._unicast_socket = UdpSocket((cfg.bind_ip, cfg.udp_port))
        self._controller = controller
        self._add_receive_callbacks()
        self._loop: asyncio.AbstractEventLoop = None

        self._known_peers: Dict[str, Peer] = {}
        self._known_peers_lock = threading.Lock()

        self._search_results: Dict[str, Dict[str, FoundResponse]] = {}
        self._search_lock = threading.Lock()

    def _add_receive_callbacks(self):
        """pass callback functions down to receiver"""
        self._broadcast_socket.add_receive_callback(self.find_callback)
        self._broadcast_socket.add_receive_callback(self.hello_callback)
        self._broadcast_socket.add_receive_callback(self.here_callback)
        self._unicast_socket.add_receive_callback(self.found_callback)
        self._unicast_socket.add_receive_callback(self.not_found_callback)

    def start(self):
        self._loop = new_loop()

        # start sockets (and their threads)
        self._unicast_socket.start(self._loop)
        self._broadcast_socket.start(self._loop)

        # run agent in background
        coro_in_background(self._serve_alive_agent(), self._loop)

        # broadcast hello message
        self._broadcast_socket.send(HelloDatagram().to_bytes())
        self._logger.debug("Started UDP controller")

    def stop(self):
        self._loop.stop()
        self._unicast_socket.stop()
        self._broadcast_socket.stop()

    @property
    def known_peers(self) -> Dict[str, Peer]:
        with self._known_peers_lock:
            return copy.deepcopy(self._known_peers)

    @property
    def known_peers_list(self) -> List[Peer]:
        return list(self.known_peers.values())

    def get_peer_by_ip(self, ip) -> Peer:
        return self.known_peers.get(ip)

    async def search(
        self, file_name: str = None, file_digest: str = None
    ) -> Dict[str, List[FoundResponse]]:
        if not file_name:
            raise InvalidSearchArgsException("Filename cannot be empty")

        if file_digest is None:
            file_digest = ""

        if file_digest != "" and not is_sha256(file_digest):
            raise InvalidSearchArgsException("File is not sha256sum")

        with self._search_lock:
            if file_name in self._search_results:
                self._logger.warning(
                    "Search | Attempted to search a file for which a search is already in progress"
                )
                raise LogicError(
                    f"There is another search for '{file_name}' in progress"
                )
            self._search_results[file_name] = dict()

        peers_available = set(self.known_peers.keys())

        def get_missing_peers():
            peers_left = peers_available.copy()
            with self._search_lock:
                for provider_ip in self._search_results[file_name].keys():
                    if provider_ip in peers_left:
                        peers_left.remove(provider_ip)
            return peers_left

        find_struct = FileDataStruct(file_name, file_digest)
        find_datagram = FindDatagram(find_struct)

        missing_peers = set()

        for retry in range(SEARCH_RETRIES + 1):
            if len(missing_peers) != 0:
                self._logger.info(
                    "Search | %s peers did not respond, retrying search for file %s with optional digest %s (%s/%s)",
                    len(missing_peers),
                    file_name,
                    file_digest,
                    retry,
                    SEARCH_RETRIES,
                )
            self._broadcast_socket.send(find_datagram.to_bytes())

            # find and found callbacks are now working
            await asyncio.sleep(FINDING_TIME)

            # check if all known peers responded and retry if not
            missing_peers = get_missing_peers()

            if len(missing_peers) == 0:
                break

        # delete peers that did not respond
        for peer_ip in missing_peers:
            self._logger.info("Search | Deleting unresponsive peer %s", peer_ip)
            self.remove_peer(peer_ip)

        # clear the dict indicating that the search is over
        with self._search_lock:
            responses: Dict[str, FoundResponse] = self._search_results.pop(file_name)

        results_dict = dict()
        for response in responses.values():
            if response.is_found:
                results_dict.setdefault(response.digest, []).append(response)

        self._logger.info(
            "Search | Found %s in %d out of %d peers",
            file_name,
            sum(len(_list) for _list in results_dict.values()),
            len(peers_available),
        )
        return results_dict

    # UDP BROADCAST RECEIVE CALLBACKS

    def hello_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_hello_datagram = HelloDatagram.from_bytes(datagram_bytes)
        if received_hello_datagram is None:
            return
        self._logger.debug("Hello | Responding with HERE to new peer %s", address[0])
        here_datagram = HereDatagram()
        self._broadcast_socket.send(here_datagram.to_bytes())

    def here_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        received_here_datagram = HereDatagram.from_bytes(datagram_bytes)

        if received_here_datagram is None:
            return
        here_struct: HereStruct = received_here_datagram.message

        ip_address = address[0]

        with self._known_peers_lock:
            is_new = ip_address not in self._known_peers
            self._known_peers[ip_address] = Peer(
                ip_address=ip_address,
                tcp_port=here_struct.tcp_port,
                unicast_port=here_struct.unicast_port,
                last_updated=datetime.datetime.now(),
            )
            self._logger.debug(
                "Here | Received HERE message from peer %s:%s", address[0], address[1]
            )
        if is_new:
            self._logger.debug("Here | Discovered peer %s:%s", address[0], address[1])

    def find_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FindDatagram
        received_find_datagram = FindDatagram.from_bytes(datagram_bytes)
        if received_find_datagram is None:
            return
        find_struct: FileDataStruct = received_find_datagram.message
        # check if peer is known
        ip_address = address[0]
        peer: Peer = self.get_peer_by_ip(ip_address)
        if peer is None:
            self._logger.debug(
                "Find | Received datagram from unknown host %s, skipping", address[0]
            )
            return

        self._logger.debug("Find | Received datagram from %s", address[0])

        try:
            file: FileMetadata = self._controller.get_file(find_struct.file_name)
            target_digest: str = find_struct.file_digest
            if target_digest and file.digest != target_digest:
                self._logger.warning(
                    "Find | Asked for file %s with digest %.8s, but local is %.8s",
                    target_digest,
                    file.digest,
                )
                raise LogicError("Hash mismatch")
            response_datagram = FoundDatagram(
                FileDataStruct(file.name, file.digest, file.size)
            )
            self._logger.debug(
                "Find | Sending positive reply for file %s with digest %.8s",
                file.name,
                file.digest,
            )
        except Exception as ex:
            response_datagram = NotFoundDatagram(find_struct)
            self._logger.debug(
                "Find | Sending negative reply for file %s with digest %.8s",
                find_struct.file_name,
                find_struct.file_digest,
            )

        unicast_port = peer.unicast_port
        self._unicast_socket.send_to(
            response_datagram.to_bytes(), ip_address, unicast_port
        )

    # UDP UNICAST RECEIVE CALLBACKS

    def found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):
        # check if datagram is of type FoundDatagram
        received_found_datagram = FoundDatagram.from_bytes(datagram_bytes)
        if received_found_datagram is None:
            return

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.known_peers:
            self._logger.warning(
                "Found | Received FoundDatagram from unknown peer %s", provider_ip
            )
            return

        # create found_response
        found_response = FoundResponse(
            received_found_datagram.message, provider_ip, True
        )

        # add provider to the set
        with self._search_lock:
            result_peers = self._search_results.get(found_response.name)
            if result_peers is not None:
                result_peers[provider_ip] = found_response

        self._logger.debug(
            "Found | Found file %s with digest %.8s, of size %s, peer %s",
            found_response.name,
            found_response.digest,
            found_response.file_size,
            provider_ip,
        )

    def not_found_callback(self, datagram_bytes: bytes, address: Tuple[str, int]):

        # check if datagram is of type FoundDatagram
        received_not_found_datagram = NotFoundDatagram.from_bytes(datagram_bytes)
        if received_not_found_datagram is None:
            return

        provider_ip = address[0]

        # check if provider is in known peers
        if provider_ip not in self.known_peers:
            self._logger.warning(
                "NotFound | Received NotFoundDatagram from unknown peer %s", provider_ip
            )
            return

        # create find_response
        not_found_response = FoundResponse(
            received_not_found_datagram.message, provider_ip, False
        )

        # add provider to the set
        with self._search_lock:
            result_peers = self._search_results.get(not_found_response.name)
            if result_peers is not None and provider_ip not in result_peers:
                # insert the peer response only if this peer was not present
                result_peers[provider_ip] = not_found_response
        self._logger.debug(
            "NotFound | Did not find file %s with optional digest %.8s, peer %s",
            not_found_response.name,
            not_found_response.digest,
            provider_ip,
        )

    def remove_peer(self, peer_ip):
        with self._known_peers_lock:
            return self._known_peers.pop(peer_ip)

    async def _serve_alive_agent(self):
        """
        thread target:
        agent that broadcasts HERE messages every 10 seconds
        and deletes peers older than 30 seconds
        """
        here_bytes = HereDatagram().to_bytes()
        while True:
            self._logger.debug("Broadcasting HERE message")
            self._broadcast_socket.send(here_bytes)
            self._delete_old_peers()
            await asyncio.sleep(10)

    def _delete_old_peers(self):
        """
        deletes peers older than 30 seconds
        """
        now = datetime.datetime.now()
        with self._known_peers_lock:
            peers = self._known_peers
            for peer_ip in list(peers.keys()):
                diff = now - peers[peer_ip].last_updated
                if diff.total_seconds() > 30:
                    self._logger.info("Removing peer %s because of inactivity", peer_ip)
                    peers.pop(peer_ip)  # delete peer from the list
