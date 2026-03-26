from sorter import merge_sort


def test_sort_odd_length():
    assert merge_sort([3, 1, 4, 1, 5]) == [1, 1, 3, 4, 5]


def test_sort_already_sorted():
    assert merge_sort([1, 2, 3]) == [1, 2, 3]


def test_sort_reverse():
    assert merge_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]


def test_sort_power_of_two():
    """Fails when len is a power of 2 due to off-by-one in _merge."""
    assert merge_sort([4, 2, 3, 1]) == [1, 2, 3, 4]
    assert merge_sort([8, 7, 6, 5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5, 6, 7, 8]


def test_sort_empty():
    assert merge_sort([]) == []


def test_sort_single():
    assert merge_sort([42]) == [42]
