import threading

from counter import Counter


def test_single_thread():
    c = Counter()
    for _ in range(100):
        c.increment()
    assert c.value() == 100


def test_concurrent_increment():
    c = Counter()
    threads = []
    for _ in range(100):
        t = threading.Thread(target=lambda: [c.increment() for _ in range(100)])
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert c.value() == 10000, f"Expected 10000, got {c.value()}"


def test_reset():
    c = Counter()
    c.increment()
    c.increment()
    c.reset()
    assert c.value() == 0
