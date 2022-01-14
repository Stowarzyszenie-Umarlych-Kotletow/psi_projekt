from cmd import Cmd
from typing import List

from udp.found_response import FoundResponse
from const import MAX_FILENAME_LENGTH


def parse_peers(peers: dict):
    index = 0
    return_str = ""
    dict_size = len(peers.items())
    for key in peers:
        peer = peers[key]
        ip = key
        return_str += f"{index}: IP: {ip} last updated: {peer['last_updated']}"
        index += 1
        if index != dict_size:
            return_str += "\n"

    return return_str


def parse_status(status_data: List):
    def parse_status_msg(file):
        msg = ""
        progress = ""
        if file['status'] == 'd':
            msg = f"downloading from {file['from']}"
            progress = f"{int(file['progress'] * 100)}%"
        if file['status'] == 'u':
            msg = f"uploading to {file['client_count']} clients"
        if file['status'] == 'h':
            msg = "hosting"
        return (msg, progress)

    index = 0
    return_str = ""
    arr_size = len(status_data)
    for file in status_data:
        status_msg, status_progress = parse_status_msg(file)
        return_str += f"{str(index):{''}>5}  | \
{file['name']:{MAX_FILENAME_LENGTH}} | \
{file['fingerprint']}     | \
{status_msg:33} | \
{f'{status_progress}'.rjust(8)}"
        index += 1
        if index != arr_size:
            return_str += "\n"
    return return_str


def parse_responses(responses: dict):
    index = 0
    return_str = ""
    arr_size = len(responses.keys())
    for key,response in responses.items():
        file_hash = response.get_hash()
        fingerprint = str(file_hash[0:16])
        file_name = response.get_name()
        provider_ip = response.get_provider_ip()
        return_str += f"{str(index):{''}>5}  | \
{file_name:{MAX_FILENAME_LENGTH}} | \
{fingerprint:{16}} | \
{provider_ip}"
        index += 1
        if index != arr_size:
            return_str += "\n"
    return return_str


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


class SimpleShell(Cmd):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    prompt = 'Ü> '
    intro = "Welcome to Überfreishare! Type ? to list commands"

    def do_exit(self, inp):
        """exit the application."""
        self.controller.stop()
        print("Bye")
        return True

    def do_list_peers(self, inp):
        """show list of known peers."""
        print(parse_peers(self.controller.get_peers()))

    def do_status(self, inp):
        """display program status."""
        print("="*102)
        print("index".ljust(7) + "| " + "name".ljust(32) + "| " + "fingerprint".ljust(13) + "| " + "status".ljust(34) + "| " + "progress")
        print(parse_status(example_status_data))
        print("="*102)

    def do_search(self, inp):
        """search for files in the network"""
        print("Searching... please wait")
        responses = self.controller.search_file(inp)
        if len(responses.keys()) == 0:
            print("No files were found in the network")
            return
        print("="*77)
        print("Files found in the network:\n")
        print("index".ljust(7) + "| " + "name".ljust(32) + "| " + "fingerprint".ljust(17) + "| " + "from")
        print(parse_responses(responses))
        print("="*77)
        provider_id = input("Select provider: ")
        print(f"TODO IN TCP {provider_id}")
