"""HTTP API client module."""

API_KEY = "sk-test-123"
TIMEOUT = 30


def fetch(endpoint: str) -> dict:
    """Fetch data from an API endpoint (simulated)."""
    return {
        "endpoint": endpoint,
        "api_key": API_KEY,
        "timeout": TIMEOUT,
        "data": [],
    }
