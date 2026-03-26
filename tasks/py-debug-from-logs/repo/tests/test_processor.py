from processor import batch_process


def test_process_partial_batch():
    assert batch_process([1, 2, 3, 4, 5], 3) == [6, 9]


def test_process_single_batch():
    assert batch_process([1, 2, 3], 10) == [6]


def test_process_exact_batch():
    """Fails when len(items) is exactly divisible by batch_size."""
    result = batch_process([1, 2, 3, 4, 5, 6], 3)
    assert result == [6, 15], f"Got {result}"


def test_process_empty():
    assert batch_process([], 3) == []
