"""HTTP API client module."""

from config import API_KEY, TIMEOUT


def fetch(endpoint: str) -> dict:
    """Fetch data from an API endpoint (simulated)."""
    return {
        "endpoint": endpoint,
        "api_key": API_KEY,
        "timeout": TIMEOUT,
        "data": [],
    }
