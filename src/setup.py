from importlib.metadata import entry_points
from setuptools import setup, find_packages
setup(
    name = 'psi',
    packages = find_packages(include=['file_transfer', 'main', 'udp', 'common']),
    entry_points={
        'console_scripts': [
            'tcp_server = file_transfer.main',
            'shell = main.main:run'
        ]
    }
)