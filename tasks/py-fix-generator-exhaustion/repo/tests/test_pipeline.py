from pipeline import consume_count, consume_sum, process


def test_consume_sum():
    assert consume_sum([1, 2, 3]) == 6


def test_consume_count():
    assert consume_count([10, 20, 30]) == 3


def test_both_consumers_receive_data():
    total, count = process([1, 2, 3, 4, 5])
    assert count == 5, f"Second consumer got {count} items, expected 5"
    assert total == 30, f"First consumer got sum={total}, expected 30"
