"""Configuration management for global store path settings."""

import json
from pathlib import Path

GLOBAL_CONFIG_PATH = Path("~/.cmdstore_config.json").expanduser()


def load_global_store_path():
    """Load the globally configured default store path, if any."""
    if GLOBAL_CONFIG_PATH.exists():
        try:
            with open(GLOBAL_CONFIG_PATH) as f:
                cfg = json.load(f)
            store = cfg.get("store")
            if isinstance(store, str) and store.strip():
                return store
        except json.JSONDecodeError:
            return None
    return None


def save_global_store_path(path: str):
    """Persistently set the global default store path."""
    GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_CONFIG_PATH, "w") as f:
        json.dump({"store": path}, f, indent=2)
