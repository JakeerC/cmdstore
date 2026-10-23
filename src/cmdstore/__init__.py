"""
cmdstore - A CLI tool to store and retrieve commands with fuzzy finding
"""

from cmdstore.cli import main
from cmdstore.errors import CmdstoreError, MalformedStoreError, StoreDataError, StoreWriteError
from cmdstore.store import CommandStore

__version__ = "0.6.0"

__all__ = [
    "CommandStore",
    "CmdstoreError",
    "MalformedStoreError",
    "StoreDataError",
    "StoreWriteError",
    "main",
]
