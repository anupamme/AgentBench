import re


def _require_string(value, field_name):
    if not value or not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")


def validate_email(value):
    _require_string(value, "email")
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValueError("invalid email format")
    return value.strip().lower()


def validate_phone(value):
    _require_string(value, "phone")
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        raise ValueError("phone must have at least 10 digits")
    return digits


def validate_zip(value):
    _require_string(value, "zip")
    if not re.match(r"^\d{5}(-\d{4})?$", value.strip()):
        raise ValueError("invalid zip code format")
    return value.strip()
