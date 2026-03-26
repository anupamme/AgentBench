import threading
from typing import Callable, List


def fetch(url: str, callback: Callable):
    """Fetch a URL in a background thread and call callback(result)."""
    def _run():
        # Simulate network fetch
        result = f"content-of-{url}"
        callback(result)
    t = threading.Thread(target=_run)
    t.start()
    t.join()


def fetch_all(urls: List[str], callback: Callable):
    """Fetch all URLs and call callback with list of results."""
    results = []
    lock = threading.Lock()

    def on_done(result):
        with lock:
            results.append(result)

    threads = []
    for url in urls:
        t = threading.Thread(target=lambda u=url: fetch(u, on_done))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    callback(results)
