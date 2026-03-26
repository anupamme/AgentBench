from utils import slugify, truncate


def make_slug(title: str) -> str:
    return slugify(truncate(title, 50))
