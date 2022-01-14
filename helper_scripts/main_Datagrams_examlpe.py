from src.controller import Controller
from src.simple_shell import SimpleShell
from src.udp.datagrams import *

if __name__ == "__main__":
    here_datagram = HereDatagram()
    here_bytes = here_datagram.to_bytes()

    here_datagram_decoded = Datagram.from_bytes(here_bytes)
    print(f"magic number: {here_datagram_decoded.get_header().get_magic_number()}")
    print(f"proto: {here_datagram_decoded.get_header().get_proto_version()}")
    print(f"tcp_port: {here_datagram_decoded.get_message().get_tcp_port()}")
    print(f"udp_port: {here_datagram_decoded.get_message().get_unicast_port()}")

    hash = "eefcd04915fc5de0abe62bc3054c561fb0b2fce265a507c884daff48f313b15e"
    find_struct = FileDataStruct("samplename", hash)
    find_datagram = FindDatagram(find_struct)
    find_bytes = find_datagram.to_bytes()

    find_datagram_decoded: FindDatagram = Datagram.from_bytes(find_bytes)

    print(f"magic number: {find_datagram_decoded.get_header().get_magic_number()}")
    print(f"proto: {find_datagram_decoded.get_header().get_proto_version()}")
    print(f"hash: {find_datagram_decoded.get_message().get_file_hash()}")
    print(f"file: {find_datagram_decoded.get_message().get_file_name()}")
    print(f"emptyhash: {find_datagram_decoded.get_message().hash_is_empty()}")

    controller = Controller()
    controller.start()
    SimpleShell(controller).cmdloop()
