from stats import get_first, get_last, get_sum


def test_get_first_normal():
    assert get_first([10, 20, 30]) == 10


def test_get_first_empty():
    assert get_first([]) is None


def test_get_last_normal():
    assert get_last([10, 20, 30]) == 30


def test_get_last_empty():
    assert get_last([]) is None


def test_get_sum():
    assert get_sum([1, 2, 3]) == 6
