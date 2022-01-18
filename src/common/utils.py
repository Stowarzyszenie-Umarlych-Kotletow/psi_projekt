import hashlib
import re

from netifaces import interfaces, ifaddresses, AF_INET
from common.config import *


def sha256sum(data):
    if type(data) == str:
        data = data.encode(ENCODING)
    return hashlib.sha256(data).hexdigest()


def all_ip4_addresses():
    ip_list = []
    for interface in interfaces():
        if_addresses = ifaddresses(interface)
        if AF_INET in if_addresses:
            for link in if_addresses[AF_INET]:
                ip_list.append(link["addr"])
    return ip_list


def all_ip4_broadcasts():
    ip_list = []
    for interface in interfaces():
        if_addresses = ifaddresses(interface)
        if AF_INET in if_addresses:
            for link in if_addresses[AF_INET]:
                if "broadcast" in link.keys():
                    ip_list.append(link["broadcast"])
    return ip_list


def get_ip4_broadcast(iface: str) -> str:
    if iface in ['', 'any', 'default']:
        return '<broadcast>'
    try:
        if_addresses = ifaddresses(iface)
        if AF_INET in if_addresses:
            for link in if_addresses[AF_INET]:
                if "broadcast" in link.keys():
                    return link["broadcast"]
    except:
        pass
    raise LogicError(f"Could not find broadcast address for interface '{iface}'")


def is_sha256(hash_string: str) -> bool:
    return bool(re.match("^[a-fA-F0-9]{64}$", hash_string))
