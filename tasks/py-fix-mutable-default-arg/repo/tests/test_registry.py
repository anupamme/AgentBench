import pytest
from registry import clear, get, register


@pytest.fixture(autouse=True)
def reset():
    clear()
    yield
    clear()


def test_register_no_tags():
    item = register("alpha")
    assert item["tags"] == []


def test_register_with_tags():
    item = register("beta", tags=["x", "y"])
    assert item["tags"] == ["x", "y"]


def test_isolated_tags():
    """Tags from one registration must not bleed into another."""
    a = register("a")
    a["tags"].append("leaked")
    b = register("b")
    assert b["tags"] == [], f"Expected [], got {b['tags']}"


def test_get():
    register("gamma", tags=["g"])
    assert get("gamma")["tags"] == ["g"]
