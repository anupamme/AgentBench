import json


def load_config(path: str) -> dict:
    """Load configuration from a JSON file."""
    with open(path) as f:
        raw = json.load(f)
    return {
        "host": raw.get("host", "localhost"),
        "port": int(raw.get("port", 8080)),
        "timeout": raw.get("timeout", "30"),  # BUG: missing int() conversion
        "debug": bool(raw.get("debug", False)),
    }
