import gc
import weakref

from event_bus import EventBus


class Subscriber:
    def __init__(self, bus: EventBus):
        bus.subscribe("event", self.handle)

    def handle(self, data):
        pass


def test_emit_works():
    bus = EventBus()
    results = []

    def handler(data):
        results.append(data)

    bus.subscribe("x", handler)
    bus.emit("x", 42)
    assert results == [42]


def test_subscriber_gc():
    """Subscriber must be GC'd when no other references exist."""
    bus = EventBus()
    sub = Subscriber(bus)
    ref = weakref.ref(sub)
    del sub
    gc.collect()
    assert ref() is None, "Subscriber not GC'd — EventBus holds a strong reference"


def test_dead_subscribers_cleaned_on_emit():
    bus = EventBus()
    sub = Subscriber(bus)
    del sub
    gc.collect()
    bus.emit("event", "data")  # must not raise
