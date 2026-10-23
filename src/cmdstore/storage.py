"""Storage utilities for safe and atomic JSON persistence."""

import contextlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from cmdstore.errors import MalformedStoreError, StoreDataError, StoreWriteError


def atomic_save_json(file_path: Path | str, data: Any, indent: int = 2) -> None:
    """Save data to a JSON file atomically using a temporary file and os.replace."""
    target_path = Path(file_path).resolve()
    target_dir = target_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    mode = None
    if target_path.exists():
        with contextlib.suppress(OSError):
            mode = stat.S_IMODE(os.stat(target_path).st_mode)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=target_dir,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as f:
            temp_path = Path(f.name)
            json.dump(data, f, indent=indent)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())

        if mode is not None:
            with contextlib.suppress(OSError):
                os.chmod(temp_path, mode)

        os.replace(temp_path, target_path)
    except Exception as e:
        if temp_path and temp_path.exists():
            with contextlib.suppress(OSError):
                temp_path.unlink()
        raise StoreWriteError(
            f"Failed to atomically write store file '{target_path}': {e}",
            path=target_path,
        ) from e


def load_json_file(
    file_path: Path | str,
    expected_type: type | tuple[type, ...] | None = None,
) -> Any:
    """Load JSON from a file, failing loudly if corrupt or top-level shape is invalid."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Store file not found: {path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise MalformedStoreError(
            f"Malformed JSON in store file '{path}': {e}. "
            "Please restore from backup or repair the file. "
            "The corrupt file has been left untouched.",
            path=path,
        ) from e
    except Exception as e:
        raise StoreDataError(
            f"Failed to read store file '{path}': {e}",
            path=path,
        ) from e

    if expected_type is not None and not isinstance(data, expected_type):
        expected_name = (
            ", ".join(t.__name__ for t in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise MalformedStoreError(
            f"Invalid structure in store file '{path}': expected {expected_name}, "
            f"got {type(data).__name__}. "
            "Please restore from backup or repair the file.",
            path=path,
        )

    return data


def validate_commands(commands: Any, path: Path | str | None = None) -> list[dict]:
    """Validate list of commands and apply defaults to missing optional fields."""
    if not isinstance(commands, list):
        path_str = f" in '{path}'" if path else ""
        raise MalformedStoreError(
            f"Invalid commands data{path_str}: expected list, got {type(commands).__name__}.",
            path=path,
        )

    validated: list[dict] = []
    for idx, item in enumerate(commands):
        if not isinstance(item, dict):
            path_str = f" in '{path}'" if path else ""
            type_name = type(item).__name__
            msg = (
                f"Invalid command record at index {idx}{path_str}: "
                f"expected object, got {type_name}."
            )
            raise MalformedStoreError(msg, path=path)

        cmd_id = item.get("id")
        if not isinstance(cmd_id, str) or not cmd_id.strip():
            path_str = f" in '{path}'" if path else ""
            raise MalformedStoreError(
                f"Missing or invalid 'id' field in command record at index {idx}{path_str}.",
                path=path,
            )

        command = item.get("command")
        if not isinstance(command, str):
            path_str = f" in '{path}'" if path else ""
            raise MalformedStoreError(
                f"Missing or invalid 'command' field in command record at index {idx}{path_str}.",
                path=path,
            )

        record = dict(item)
        desc = record.get("description")
        record["description"] = str(desc) if desc is not None and isinstance(desc, str) else ""

        tags = record.get("tags")
        record["tags"] = list(tags) if isinstance(tags, (list, tuple)) else []

        tool = record.get("tool")
        record["tool"] = str(tool) if tool is not None and isinstance(tool, str) else ""

        created = record.get("created_at")
        record["created_at"] = (
            str(created) if created is not None and isinstance(created, str) else ""
        )

        used = record.get("used_count")
        if not isinstance(used, int):
            try:
                record["used_count"] = int(used) if used is not None else 0
            except (ValueError, TypeError):
                record["used_count"] = 0

        validated.append(record)

    return validated


def validate_config(config: Any, path: Path | str | None = None) -> dict:
    """Validate that configuration is a dictionary."""
    if not isinstance(config, dict):
        path_str = f" in '{path}'" if path else ""
        raise MalformedStoreError(
            f"Invalid configuration data{path_str}: expected dict, got {type(config).__name__}.",
            path=path,
        )
    return config
