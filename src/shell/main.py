import argparse
import logging.config
from pathlib import Path

import yaml
from common.config import Config

from shell.controller import Controller
from shell.simple_shell import SimpleShell


def configure_logging():
    # this is the project root path
    path = Path(__file__).parent.parent.joinpath("log.yml")
    with open(path, "r") as reader:
        config = yaml.safe_load(reader)
    logging.config.dictConfig(config)

def parse_cmdline():
    cfg = Config()

    parser = argparse.ArgumentParser(description="Simple P2P client", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--bind-ip", help="IP to bind for file transfer and discovery", type=str, default=cfg.bind_ip)
    parser.add_argument("--tcp-port", help="TCP port to use for file transfer", type=int, default=cfg.tcp_port)
    parser.add_argument("--udp-port", help="UDP port to use for file discovery", type=int, default=cfg.udp_port)
    parser.add_argument("--broadcast-iface", help="Interface to broadcast on for peer/file discovery", type=str, default=cfg.broadcast_iface)
    parser.add_argument("--broadcast-port", help="UDP port to broadcast on for peer/file discovery", type=int, default=cfg.broadcast_port)
    parser.add_argument("--broadcast-drop-chance", help="Percentage chance to drop incoming broadcast packet", type=int, default=cfg.broadcast_drop_chance)
    parser.add_argument("--broadcast-drop-in-row", help="Number of packets to be dropped at once",type=int, default=cfg.broadcast_drop_in_row)
    args = parser.parse_args()
    args_dict = {k: v for (k, v) in args._get_kwargs()}
    cfg.update(args_dict)

def run():
    parse_cmdline()
    configure_logging()
    controller = Controller()
    print("Starting... this might take a bit")
    try:
        controller.start()
    except Exception as exc:
        print("Fatal error:", exc)
        exit(1)
    SimpleShell(controller).cmdloop()


if __name__ == "__main__":
    run()
