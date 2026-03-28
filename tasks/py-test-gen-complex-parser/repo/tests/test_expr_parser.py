from expr_parser import evaluate


def test_integer():
    assert evaluate("42") == 42


def test_addition():
    assert evaluate("1 + 2") == 3


def test_subtraction():
    assert evaluate("10 - 4") == 6
