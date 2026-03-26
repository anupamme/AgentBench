import time
import urllib.request
import urllib.error


def fetch_data(url: str) -> str:
    """Fetch data from a URL, returning the response body as a string."""
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")
