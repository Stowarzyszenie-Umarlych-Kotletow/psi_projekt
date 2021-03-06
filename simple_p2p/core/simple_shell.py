import asyncio
import random
from cmd import Cmd

from prettytable import PrettyTable

from simple_p2p.common.config import FINGERPRINT_LENGTH
from simple_p2p.common.exceptions import FileDuplicateException, NotFoundError
from simple_p2p.common.models import FileStatus
from simple_p2p.core.controller import FileStateContext, Controller
from simple_p2p.udp.found_response import FoundResponse


class SimpleShell(Cmd):
    def __init__(self, controller: Controller):
        super().__init__()
        self._controller: Controller = controller

    prompt = "> "
    intro = "Welcome to SimpleP2P. Type ? to list commands"

    def do_exit(self, inp):
        """exit: exit the application"""
        self._controller.stop()
        print("Bye")
        return True

    def do_peers(self, inp):
        """peers: show list of known peers"""
        peers_table = PrettyTable()
        peers_table.field_names = ["ID", "IP address", "Last updated"]
        peers = self._controller.known_peers_list
        for (index, peer) in enumerate(peers):
            peers_table.add_row([index, peer.ip_address, peer.last_updated])
        print(peers_table)

    def do_status(self, inp):
        """status: display program status"""

        def parse_status_msg(file: FileStateContext):
            meta = file.file_meta
            provider = file.provider
            consumers = file.consumers

            if meta.status == FileStatus.DOWNLOADING:
                peer = (
                    f"{provider.endpoint[0]}"
                    if provider and provider.endpoint
                    else "searching"
                )
                progress = 0 if not meta.size else meta.current_size / meta.size
                return f"DOWNLOADING", f"{progress * 100:.2f}%", peer
            elif len(consumers) > 0:
                return f"UPLOADING", "---", f"{len(consumers)} clients"
            else:
                return meta.status.name, "---", "---"

        status_table = PrettyTable()
        status_table.field_names = [
            "ID",
            "File name",
            "Fingerprint",
            "Size",
            "Status",
            "Progress",
            "Peer(s)",
        ]
        status_data = list(self._controller.state.values())
        for (index, file) in enumerate(status_data):
            status_msg, status_progress, peers = parse_status_msg(file)
            meta = file.file_meta
            status_table.add_row(
                [
                    index,
                    meta.name,
                    meta.digest[:FINGERPRINT_LENGTH],
                    meta.size,
                    status_msg,
                    status_progress,
                    peers,
                ]
            )

        print(status_table)

    def _do_search(self, inp, check_duplicate=False):
        try:
            self._controller.get_file(inp)
            if check_duplicate:
                print("File already exists in your local repository")
                return
        except NotFoundError:
            # that is expected
            pass
        except Exception as err:
            print("Error searching file:", err)
            return
        print("Searching... please wait")
        responses = asyncio.run(self._controller.search_file(inp))
        if len(responses) == 0:
            print("No files were found in the network")
            return
        search_table = PrettyTable()
        search_table.field_names = ["ID", "Name", "Fingerprint", "Size", "From"]

        for (index, (digest, providers)) in enumerate(responses.items()):
            name = providers[0].name
            size = providers[0].file_size
            search_table.add_row(
                [index, name, digest[:FINGERPRINT_LENGTH], size, f"{len(providers)} peers"]
            )

        print("Files found in the network:")
        print(search_table)
        return responses

    def do_search(self, inp):
        """search <file_name>: search for file in the network"""
        self._do_search(inp)

    def do_download(self, inp):
        """download <file_name>: download file with given name from the network"""
        responses = self._do_search(inp, True)
        if responses is None:
            return
        # handle multiple versions
        if len(responses) == 1:
            target_digest = next(iter(responses))
        else:
            print("Found multiple versions. Please choose one.")
            try:
                provider_id = int(input("Select provider index: "))
                target_digest = list(responses.keys())[provider_id]
            except:
                print("Invalid choice")
                return
        # start the download
        print("Starting download...")
        response: FoundResponse = random.choice(responses[target_digest])
        target_ip = response.provider_ip
        peer = self._controller.get_peer_by_ip(target_ip)
        target_port = peer.tcp_port
        try:
            self._controller.schedule_download(
                response.name,
                response.digest,
                response.file_size,
                (target_ip, target_port),
            )
        except FileDuplicateException as err:
            print(err)

    def do_add(self, inp):
        """add <file_path>: add file to the local repository with absolute path"""
        try:
            result = self._controller.add_file(inp)
            print(f"Added file {result.name} with digest {result.digest}")
        except Exception as err:
            print("Error adding file: ", err)

    def do_remove(self, inp):
        """remove <file_name>: remove file from local repository"""

        try:
            file = self._controller.get_file(inp)
            print(
                f"Deleting file '{file.name}' with status '{file.status}' from the repository"
            )
            self._controller.remove_file(file.name)
            print(f"Done. The file is still available at '{file.path}'")
        except Exception as e:
            print("Cannot remove the file: ", e)

    def do_info(self, inp):
        """status: display detailed info about the specified file"""
        try:
            file = self._controller.get_file(inp)
            table = PrettyTable()
            table.field_names = ["Name", "Fingerprint", "Status", "Size", "Path"]
            table.add_row(
                [
                    file.name,
                    file.digest[:FINGERPRINT_LENGTH],
                    file.status.name,
                    file.size,
                    file.path,
                ]
            )
            print(table)
        except Exception as e:
            print("Not found: ", e)

    def do_stop(self, inp):
        """stop: stop daemon"""
        if self._controller.is_running():
            print("Stopping daemon...")
            self._controller.stop()
        else:
            print("Daemon is not running")

    def do_start(self, inp):
        """start: start daemon"""
        if not self._controller.is_running():
            print("Starting daemon...")
            self._controller.start()
        else:
            print("Daemon is already running")
