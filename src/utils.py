import hashlib

from netifaces import interfaces, ifaddresses, AF_INET

from const import *


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
                ip_list.append(link['addr'])
    return ip_list


def all_ip4_broadcasts():
    ip_list = []
    for interface in interfaces():
        if_addresses = ifaddresses(interface)
        if AF_INET in if_addresses:
            for link in if_addresses[AF_INET]:
                if 'broadcast' in link.keys():
                    ip_list.append(link['broadcast'])
    return ip_list
