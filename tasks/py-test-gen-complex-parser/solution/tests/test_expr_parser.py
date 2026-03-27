import pytest
from expr_parser import evaluate, ParseError


def test_integer():
    assert evaluate("42") == 42


def test_addition():
    assert evaluate("1 + 2") == 3


def test_subtraction():
    assert evaluate("10 - 4") == 6


def test_multiplication():
    assert evaluate("3 * 4") == 12


def test_division():
    assert evaluate("10 / 2") == 5


def test_precedence_mul_over_add():
    assert evaluate("2 + 3 * 4") == 14


def test_precedence_add_then_mul():
    assert evaluate("2 * 3 + 4") == 10


def test_parentheses_override_precedence():
    assert evaluate("(2 + 3) * 4") == 20


def test_nested_parentheses():
    assert evaluate("((2 + 3) * (4 - 1))") == 15


def test_unary_minus():
    assert evaluate("-5") == -5


def test_unary_minus_in_expression():
    assert evaluate("10 + -3") == 7


def test_complex_expression():
    assert evaluate("2 + 3 * 4 - (6 / 2)") == 11


def test_division_by_zero():
    with pytest.raises(ParseError, match="Division by zero"):
        evaluate("10 / 0")


def test_unmatched_paren():
    with pytest.raises(ParseError):
        evaluate("(1 + 2")


def test_invalid_character():
    with pytest.raises(ParseError):
        evaluate("1 + @")


def test_trailing_token():
    with pytest.raises(ParseError):
        evaluate("1 + 2 3")
