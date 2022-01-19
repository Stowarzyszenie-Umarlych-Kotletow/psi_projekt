from importlib.metadata import entry_points
from setuptools import setup, find_packages

setup(
    name="simple_p2p",
    packages=find_packages(
        include=[
            "simple_p2p",
            "simple_p2p.file_transfer",
            "simple_p2p.core",
            "simple_p2p.udp",
            "simple_p2p.common",
            "simple_p2p.repository",
        ]
    ),
    entry_points={"console_scripts": ["simple-p2p = simple_p2p.core.main:run"]},
    package_data={"simple_p2p": ["log.yml"]},
    include_package_data=True,
)
