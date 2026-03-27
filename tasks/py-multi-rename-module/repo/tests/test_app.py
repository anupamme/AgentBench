from utils import slugify, truncate, capitalize_words
from app import make_slug
from models import Article


def test_slugify():
    assert slugify("Hello World") == "hello-world"


def test_truncate():
    assert truncate("abcdef", 3) == "abc"


def test_capitalize():
    assert capitalize_words("hello world") == "Hello World"


def test_make_slug():
    assert make_slug("Hello World") == "hello-world"


def test_article():
    a = Article("hello world")
    assert a.title == "Hello World"
