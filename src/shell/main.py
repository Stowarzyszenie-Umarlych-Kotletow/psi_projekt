import logging.config
from pathlib import Path

import yaml

from shell.controller import Controller
from shell.simple_shell import SimpleShell

def configure_logging():
    path = Path(__file__).parent.parent.joinpath("log.yml")
    with open(path, "r") as reader:
        config = yaml.safe_load(reader)
    logging.config.dictConfig(config)

def run():
    configure_logging()
    controller = Controller()
    controller.start()
    SimpleShell(controller).cmdloop()

if __name__ == "__main__":
    run()