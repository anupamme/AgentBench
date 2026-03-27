import time
import urllib.request
import urllib.error

MAX_RETRIES = 3


def fetch_data(url: str) -> str:
    """Fetch data from a URL, retrying up to 3 times on failure."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode("utf-8")
        except urllib.error.URLError as e:
            last_exc = e
            time.sleep(0)
    raise last_exc
