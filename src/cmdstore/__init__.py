"""
cmdstore - A CLI tool to store and retrieve commands with fuzzy finding
"""

from cmdstore.cli import main
from cmdstore.store import CommandStore

__all__ = ["CommandStore", "main"]
