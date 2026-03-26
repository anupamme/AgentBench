from processor import process_all


def test_process_all_items():
    assert process_all([1, 2, 3]) == [2, 4, 6]


def test_process_empty():
    assert process_all([]) == []


def test_process_single():
    assert process_all([5]) == [10]
