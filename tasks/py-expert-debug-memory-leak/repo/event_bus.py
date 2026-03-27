from typing import Callable


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        self._subscribers.setdefault(event, []).append(handler)

    def emit(self, event: str, *args) -> None:
        for handler in list(self._subscribers.get(event, [])):
            handler(*args)

    def subscriber_count(self, event: str) -> int:
        return len(self._subscribers.get(event, []))
