from sorter import binary_search


def test_find_first():
    assert binary_search([1, 2, 3, 4, 5], 1) == 0


def test_find_middle():
    assert binary_search([1, 2, 3, 4, 5], 3) == 2


def test_not_found():
    assert binary_search([1, 2, 3, 4, 5], 99) == -1


def test_find_last():
    """Fails due to off-by-one: hi is initialised to len-2 instead of len-1."""
    assert binary_search([1, 2, 3, 4, 5], 5) == 4


def test_single_element():
    assert binary_search([7], 7) == 0


def test_two_elements_find_second():
    """Also fails because hi starts at 0 (len-2=0) and never checks index 1."""
    assert binary_search([3, 9], 9) == 1
