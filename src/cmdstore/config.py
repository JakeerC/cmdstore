"""Configuration management for global store path settings."""

from pathlib import Path

from cmdstore.storage import atomic_save_json, load_json_file

GLOBAL_CONFIG_PATH = Path("~/.cmdstore_config.json").expanduser()


def load_global_store_path(config_path: Path | None = None) -> str | None:
    """Load the globally configured default store path, if any."""
    path = config_path or GLOBAL_CONFIG_PATH
    if path.exists():
        cfg = load_json_file(path, expected_type=dict)
        store = cfg.get("store")
        if isinstance(store, str) and store.strip():
            return store.strip()
    return None


def save_global_store_path(path: str, config_path: Path | None = None) -> None:
    """Persistently set the global default store path."""
    target_path = config_path or GLOBAL_CONFIG_PATH
    atomic_save_json(target_path, {"store": path}, indent=2)
