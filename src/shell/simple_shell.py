from cmd import Cmd
from typing import List

from shell.controller import FileStateContext
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
        progress = 1 if not meta.size else meta.current_size / meta.size
        if provider:
            endpoint_name = ":".join(provider.endpoint) if provider.endpoint else 'unknown'
            return (
                f"downloading from {endpoint_name}",
                f"{progress * 100}%",
            )
        elif len(consumers) > 0:
            return (f"uploading to {len(consumers)} clients", "")
        elif file.file_meta.status == 'sharing':
            return ("sharing", "")
        return ("", "")

    index = 0
    return_str = ""
    for file in status_data:
        status_msg, status_progress = parse_status_msg(file)
        meta = file.file_meta
        return_str += f"{str(index):{MAX_RSP_ID_SIZE}}  | {meta.name:{MAX_FILENAME_LENGTH}}  | \
{meta.digest:.16s}     | {status_msg:{MAX_STATUS_MSG_SIZE}}| {f'{status_progress}'.rjust(MAX_PROGRESS_MSG_LEN)}\n"
        index += 1
    return return_str


def parse_responses(responses: list):
    return_str = ""
    for (index, response) in enumerate(responses):
        return_str += f"{str(index):{MAX_RSP_ID_SIZE}}  | {response.get_name():{MAX_FILENAME_LENGTH}}  | \
{str(response.get_hash()[:PEER_FP_SHORT]):{PEER_FP_SHORT}}| {response.get_provider_ip()}\n"
    return return_str


class SimpleShell(Cmd):
    def __init__(self, controller):
        super().__init__()
        self._controller = controller

    prompt = "Ü> "
    intro = "Welcome to Überfreishare! Type ? to list commands"

    def do_exit(self, inp):
        """exit the application."""
        self._controller.stop()
        print("Bye")
        return True

    def do_list_peers(self, inp):
        """show list of known peers."""
        print(parse_peers(self._controller.get_peers()), end="")

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
        status = self._controller._state.values()
        print(parse_status(status), end="")
        print("=" * STATUS_HR_LEN)

    def do_search(self, inp):
        """search for files in the network"""
        print("Searching... please wait")
        responses = self._controller.search_file(inp)
        if len(responses.keys()) == 0:
            print("No files were found in the network")
            return
        responses = list(responses.values())
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
        provider_id = int(input("Select provider: "))
        response: FoundResponse = responses[provider_id]
        target_ip = response.get_provider_ip()
        peer = self._controller.get_peer(target_ip)
        target_port = peer['tcp_port']
        self._controller.schedule_download(response.get_name(), response.get_hash(), 0, (target_ip, target_port))

    def do_add(self, inp):
        result = self._controller.add_file(inp)
        print(f"Added file {result.name} with digest {result.digest}")


example_status_data = [
    {
        "name": "Przygody koziołka.avi1111111111",
        "fingerprint": "49ba7b56",
        "status": "d",  # todo enum
        "progress": 0.05,
        "from": "10.1.1.34",
        "client_count": None,
    },
    {
        "name": "zdjecia.zip",
        "fingerprint": "0e2fa1ab",
        "status": "d",
        "progress": 0.3,
        "from": "10.1.1.3",
        "client_count": None,
    },
    {
        "name": "kody GTA.txt",
        "fingerprint": "2e239528",
        "status": "u",
        "progress": 0.05,
        "client_count": 2,
    },
    {
        "name": "pan_tadeusz.txt",
        "fingerprint": "dbbbbbbb",
        "status": "h",
        "progress": None,
        "client_count": None,
    },
]
