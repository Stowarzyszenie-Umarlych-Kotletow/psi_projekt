import asyncio
import random
from cmd import Cmd
from typing import List, Dict
from shell.controller import FileStateContext, Controller
from udp.found_response import FoundResponse
from common.config import (
    MAX_FILENAME_LENGTH,
    MAX_RSP_ID_SIZE,
    PEER_FP_SHORT,
    FILE_FP_HR_LEN,
    MAX_PROGRESS_MSG_LEN,
    MAX_STATUS_MSG_SIZE,
    TABLE_SEP_LEN,
    SEARCH_HR_LEN,
    STATUS_HR_LEN,
)


def parse_peers(peers: dict):
    index = 0
    return_str = ""
    for key in peers:
        peer = peers[key]
        ip = key
        return_str += f"{index}: IP: {ip} last updated: {peer['last_updated']}\n"
        index += 1
    return return_str


def parse_status(status_data: List[FileStateContext]):
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

    index = 0
    return_str = ""
    for file in status_data:
        status_msg, status_progress = parse_status_msg(file)
        meta = file.file_meta
        return_str += f"{str(index):{MAX_RSP_ID_SIZE}}  | {meta.name:{MAX_FILENAME_LENGTH}}  | \
{meta.digest:.8s}     | {status_msg:{MAX_STATUS_MSG_SIZE}}| {f'{status_progress}'.rjust(MAX_PROGRESS_MSG_LEN)}\n"
        index += 1
    return return_str


def parse_responses(responses: Dict[str, List[FoundResponse]]):
    return_str = ""
    for (index, (digest, providers)) in enumerate(responses.items()):
        name = providers[0].name
        return_str += f"{index:{MAX_RSP_ID_SIZE}}  | {name:{MAX_FILENAME_LENGTH}}  | \
{digest:.8s} | {len(providers)} peers\n"
    return return_str


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
        print(parse_peers(self._controller.known_peers), end="")

    def do_status(self, inp):
        """display program status."""
        print(
            "=" * STATUS_HR_LEN
            + "\n"
            + "index".ljust(MAX_RSP_ID_SIZE + TABLE_SEP_LEN)
            + "| "
            + "name".ljust(MAX_FILENAME_LENGTH + TABLE_SEP_LEN)
            + "| "
            + "fingerprint".ljust(FILE_FP_HR_LEN)
            + "| "
            + "status".ljust(MAX_STATUS_MSG_SIZE)
            + "| "
            + "progress"
        )
        status = self._controller.state.values()
        print(parse_status(list(status)), end="")
        print("=" * STATUS_HR_LEN)

    def do_search(self, inp):
        """search for files in the network"""
        print("Searching... please wait")
        responses = asyncio.run(self._controller.search_file(inp))
        if len(responses) == 0:
            print("No files were found in the network")
            return

        print(
            "=" * SEARCH_HR_LEN
            + "\nFiles found in the network:\n"
            + "index".ljust(MAX_RSP_ID_SIZE + TABLE_SEP_LEN)
            + "| "
            + "name".ljust(MAX_FILENAME_LENGTH + TABLE_SEP_LEN)
            + "| "
            + "fingerprint".ljust(PEER_FP_SHORT)
            + "| "
            + "from"
        )
        print(parse_responses(responses), end="")
        print("=" * SEARCH_HR_LEN)
        if len(responses) == 1:
            target_digest = next(iter(responses))
        else:
            print("Found multiple versions. Please choose one.")
            provider_id = int(input("Select provider index: "))
            target_digest = list(responses.keys())[provider_id]
        response: FoundResponse = random.choice(responses[target_digest])
        target_ip = response.provider_ip
        peer = self._controller.get_peer_by_ip(target_ip)
        target_port = peer['tcp_port']
        self._controller.schedule_download(response.name, response.digest, 0, (target_ip, target_port))

    def do_add(self, inp):
        result = self._controller.add_file(inp)
        print(f"Added file {result.name} with digest {result.digest}")
