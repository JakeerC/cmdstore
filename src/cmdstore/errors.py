"""Exception classes for cmdstore."""

from pathlib import Path


class CmdstoreError(Exception):
    """Base exception for all cmdstore errors."""


class StoreDataError(CmdstoreError):
    """Base exception for store data reading or validation errors."""

    def __init__(self, message: str, path: Path | str | None = None):
        super().__init__(message)
        self.path = Path(path) if path else None


class MalformedStoreError(StoreDataError):
    """Raised when a store file contains malformed JSON or unexpected top-level structure."""


class StoreWriteError(StoreDataError):
    """Raised when an atomic write to a store file fails."""


class FzfError(CmdstoreError):
    """Raised when fzf process execution fails with an unexpected return code."""

    def __init__(self, message: str, returncode: int | None = None, stderr: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr
