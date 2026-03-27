import threading
from typing import Any


class QueueEmpty(Exception):
    pass


class QueueFull(Exception):
    pass


class BoundedQueue:
    def __init__(self, maxsize: int):
        self._maxsize = maxsize
        self._queue = []
        self._lock = threading.Lock()
        self._not_full = threading.Condition(self._lock)
        self._not_empty = threading.Condition(self._lock)

    def put(self, item: Any, timeout: float = None) -> None:
        with self._not_full:
            if not self._not_full.wait_for(
                lambda: len(self._queue) < self._maxsize, timeout=timeout
            ):
                raise QueueFull("Queue is full")
            self._queue.append(item)
            self._not_empty.notify()

    def get(self, timeout: float = None) -> Any:
        with self._not_empty:
            if not self._not_empty.wait_for(
                lambda: len(self._queue) > 0, timeout=timeout
            ):
                raise QueueEmpty("Queue is empty")
            item = self._queue.pop(0)
            self._not_full.notify()
            return item

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0
