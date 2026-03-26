import re


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, appending suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def pad_left(text: str, width: int, char: str = " ") -> str:
    """Pad text on the left to reach the given width."""
    if len(text) >= width:
        return text
    return char * (width - len(text)) + text


def remove_vowels(text: str) -> str:
    """Remove all vowels (a, e, i, o, u) from text."""
    return re.sub(r"[aeiouAEIOU]", "", text)
