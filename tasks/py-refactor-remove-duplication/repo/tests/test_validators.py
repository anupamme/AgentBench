import pytest
from validators import validate_email, validate_phone, validate_zip


def test_email_valid():
    assert validate_email("user@example.com") == "user@example.com"


def test_email_empty():
    with pytest.raises(ValueError):
        validate_email("")


def test_email_none():
    with pytest.raises(ValueError):
        validate_email(None)


def test_phone_valid():
    assert validate_phone("(555) 123-4567") == "5551234567"


def test_phone_empty():
    with pytest.raises(ValueError):
        validate_phone("")


def test_zip_valid():
    assert validate_zip("12345") == "12345"


def test_zip_invalid():
    with pytest.raises(ValueError):
        validate_zip("abc")


def test_zip_empty():
    with pytest.raises(ValueError):
        validate_zip("")
