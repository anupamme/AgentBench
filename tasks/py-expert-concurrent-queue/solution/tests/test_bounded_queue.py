import threading

import pytest
from bounded_queue import BoundedQueue, QueueEmpty, QueueFull


def test_basic_put_get():
    q = BoundedQueue(3)
    q.put(1)
    q.put(2)
    assert q.get() == 1
    assert q.get() == 2


def test_size():
    q = BoundedQueue(5)
    assert q.size() == 0
    q.put("a")
    assert q.size() == 1


def test_is_empty():
    q = BoundedQueue(2)
    assert q.is_empty()
    q.put(1)
    assert not q.is_empty()


def test_put_timeout_raises_when_full():
    q = BoundedQueue(1)
    q.put("x")
    with pytest.raises(QueueFull):
        q.put("y", timeout=0.05)


def test_get_timeout_raises_when_empty():
    q = BoundedQueue(2)
    with pytest.raises(QueueEmpty):
        q.get(timeout=0.05)


def test_fifo_order():
    q = BoundedQueue(5)
    for i in range(5):
        q.put(i)
    for i in range(5):
        assert q.get() == i


def test_multi_producer_consumer():
    q = BoundedQueue(10)
    results = []
    lock = threading.Lock()

    def producer(n):
        for i in range(n):
            q.put(i)

    def consumer(n):
        for _ in range(n):
            item = q.get(timeout=2.0)
            with lock:
                results.append(item)

    n = 20
    t1 = threading.Thread(target=producer, args=(n,))
    t2 = threading.Thread(target=consumer, args=(n,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert len(results) == n


def test_blocking_unblocks_when_space_available():
    q = BoundedQueue(1)
    q.put("first")
    unblocked = threading.Event()

    def writer():
        q.put("second", timeout=1.0)
        unblocked.set()

    t = threading.Thread(target=writer)
    t.start()
    q.get()
    assert unblocked.wait(timeout=1.0)
    t.join()
