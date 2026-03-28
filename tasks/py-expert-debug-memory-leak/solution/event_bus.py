import weakref
from collections.abc import Callable


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list] = {}

    def subscribe(self, event: str, handler: Callable) -> None:
        if hasattr(handler, "__self__"):
            ref = weakref.WeakMethod(handler)
        else:
            ref = weakref.ref(handler)
        self._subscribers.setdefault(event, []).append(ref)

    def emit(self, event: str, *args) -> None:
        alive = []
        for ref in self._subscribers.get(event, []):
            handler = ref()
            if handler is not None:
                handler(*args)
                alive.append(ref)
        if event in self._subscribers:
            self._subscribers[event] = alive

    def subscriber_count(self, event: str) -> int:
        return sum(1 for ref in self._subscribers.get(event, []) if ref() is not None)
