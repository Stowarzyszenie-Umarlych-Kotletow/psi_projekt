import asyncio
import random
from cmd import Cmd

from prettytable import PrettyTable

from common.config import FINGERPRINT_LENGTH
from file_transfer.exceptions import FileDuplicateException
from shell.controller import FileStateContext, Controller
from udp.found_response import FoundResponse


class SimpleShell(Cmd):
    def __init__(self, controller: Controller):
        super().__init__()
        self._controller: Controller = controller

    prompt = "Ü> "
    intro = "Welcome to Überfreishare! Type ? to list commands"

    def do_exit(self, inp):
        """exit the application."""
        self._controller.stop()
        print("Bye")
        return True

    def do_list_peers(self, inp):
        """show list of known peers."""
        peers_table = PrettyTable()
        peers_table.field_names = ['ID', 'IP address', 'Last updated']
        peers = self._controller.known_peers_list
        index = 0
        for peer in peers:
            peers_table.add_row([index, peer.ip_address, peer.last_updated])
            index += 1
        print(peers_table)

    def do_status(self, inp):
        """display program status."""

        def parse_status_msg(file: FileStateContext):
            meta = file.file_meta
            provider = file.provider
            consumers = file.consumers
            progress = 0 if not meta.size else meta.current_size / meta.size
            if provider:
                endpoint_name = ":".join(provider.endpoint) if provider.endpoint else 'unknown'
                return (
                    f"downloading from {endpoint_name}",
                    f"{progress * 100}%",
                )
            elif len(consumers) > 0:
                return (f"uploading to {len(consumers)} clients", "")
            else:
                return (meta.status, "")

        status_table = PrettyTable()
        status_table.field_names = ['ID', 'File name', 'Fingerprint', 'Status', 'Progress']
        status_data = list(self._controller.state.values())
        index = 0
        for file in status_data:
            status_msg, status_progress = parse_status_msg(file)
            meta = file.file_meta
            status_table.add_row([index, meta.name, meta.digest[:FINGERPRINT_LENGTH], status_msg, status_progress])
            index += 1

        print(status_table)

    def do_download(self, inp):
        """search and download for files in the network"""
        # todo check if repo does not contain such filename
        print("Searching... please wait")
        responses = asyncio.run(self._controller.search_file(inp))
        if len(responses) == 0:
            print("No files were found in the network")
            return
        search_table = PrettyTable()
        search_table.field_names = ['ID', 'Name', 'Fingerprint', 'From']

        for (index, (digest, providers)) in enumerate(responses.items()):
            name = providers[0].name
            search_table.add_row([index, name, digest[:FINGERPRINT_LENGTH], f"{len(providers)} peers"])

        print(search_table)

        if len(responses) == 1:
            target_digest = next(iter(responses))
        else:
            print("Found multiple versions. Please choose one.")
            provider_id = int(input("Select provider index: "))
            target_digest = list(responses.keys())[provider_id]
        print("Starting download...")
        response: FoundResponse = random.choice(responses[target_digest])
        target_ip = response.provider_ip
        peer = self._controller.get_peer_by_ip(target_ip)
        target_port = peer.tcp_port
        try:
            self._controller.schedule_download(response.name, response.digest, 0, (target_ip, target_port))
        except FileDuplicateException as err:
            print(err)

    def do_add(self, inp):
        try:
            result = self._controller.add_file(inp)
            print(f"Added file {result.name} with digest {result.digest}")
        except Exception as err:
            print("Error adding file: " + str(err))
