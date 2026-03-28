from formatter import format_currency, format_number, format_percentage


def test_format_number_explicit():
    assert format_number(3.14159, 2) == "3.14"


def test_format_number_default_decimals():
    assert format_number(3.14159) == "3.14"


def test_format_number_zero_decimals():
    assert format_number(3.14159, 0) == "3"


def test_format_currency():
    assert format_currency(9.99) == "$9.99"


def test_format_percentage():
    assert format_percentage(0.75) == "75.0%"
