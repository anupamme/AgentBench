import re


def validate_email(value):
    if not value or not isinstance(value, str):
        raise ValueError("email must be a non-empty string")
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("invalid email format")
    return value.strip().lower()


def validate_phone(value):
    if not value or not isinstance(value, str):
        raise ValueError("phone must be a non-empty string")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        raise ValueError("phone must have at least 10 digits")
    return digits


def validate_zip(value):
    if not value or not isinstance(value, str):
        raise ValueError("zip must be a non-empty string")
    if not re.match(r"^\d{5}(-\d{4})?$", value.strip()):
        raise ValueError("invalid zip code format")
    return value.strip()
