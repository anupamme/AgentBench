def slugify(text: str) -> str:
    return text.lower().replace(" ", "-")


def truncate(text: str, n: int) -> str:
    return text[:n] if len(text) > n else text


def capitalize_words(text: str) -> str:
    return " ".join(w.capitalize() for w in text.split())
