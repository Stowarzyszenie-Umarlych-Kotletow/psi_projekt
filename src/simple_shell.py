from cmd import Cmd
from typing import List

from udp.found_response import FoundResponse


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
        tmp_str = ""
        if file['status'] == 'd':
            tmp_str += f"downloading from {file['from']} ({file['progress'] * 100}%)"
        if file['status'] == 'u':
            tmp_str += f"uploading to {file['client_count']} clients"
        if file['status'] == 'h':
            tmp_str += f"hosting"
        return tmp_str

    index = 0
    return_str = ""
    arr_size = len(status_data)
    for file in status_data:
        status_msg = parse_status_msg(file)
        return_str += f"{index}: \tname: {file['name']} fingerprint: {file['fingerprint']} status: " + status_msg
        index += 1
        if index != arr_size:
            return_str += "\n"
    return return_str


def parse_responses(responses: dict):
    index = 0
    return_str = "Files found in the network:\n"
    arr_size = len(responses.keys())
    for key in responses:
        response: FoundResponse = responses[key]
        file_hash = response.get_hash()
        fingerprint = file_hash[0:16]
        file_name = response.get_name()
        provider_ip = response.get_provider_ip()
        return_str += f"{index}: \tname: \"{file_name}\" fingerprint: \"{fingerprint}\" from {provider_ip}"
        index += 1
        if index != arr_size:
            return_str += "\n"
    return return_str


example_status_data = [
    {
        "name": "Przygody koziołka.avi",
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
        print(parse_status(example_status_data))

    def do_search(self, inp):
        """search for files in the network"""
        print("Searching... please wait")
        responses = self.controller.search_file(inp)
        if len(responses.keys()) == 0:
            print("No files were found in the network")
            return
        print(parse_responses(responses))
        provider_id = input("Select provider: ")
        print(f"TODO IN TCP {provider_id}")
