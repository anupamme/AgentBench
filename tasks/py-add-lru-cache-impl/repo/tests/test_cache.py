from cache import LRUCache


def test_get_missing():
    c = LRUCache(2)
    assert c.get(1) == -1


def test_put_and_get():
    c = LRUCache(2)
    c.put(1, 10)
    assert c.get(1) == 10


def test_evicts_lru():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.put(3, 3)  # evicts key 1
    assert c.get(1) == -1
    assert c.get(2) == 2
    assert c.get(3) == 3


def test_get_updates_recency():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    c.get(1)     # access key 1 → key 2 is now LRU
    c.put(3, 3)  # evicts key 2
    assert c.get(2) == -1
    assert c.get(1) == 1


def test_update_existing():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(1, 100)
    assert c.get(1) == 100
