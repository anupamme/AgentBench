import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from routes import store


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the in-memory store before each test."""
    store._todos.clear()
    store._next_id = 1
    yield


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_create_todo(client):
    resp = client.post("/todos", json={"title": "Buy milk"})
    assert resp.status_code == 201
    data = resp.json
    assert data["title"] == "Buy milk"
    assert data["done"] is False
    assert data["id"] == 1


def test_get_todo(client):
    client.post("/todos", json={"title": "Write tests"})
    resp = client.get("/todos/1")
    assert resp.status_code == 200
    assert resp.json["title"] == "Write tests"


def test_get_todo_not_found(client):
    resp = client.get("/todos/999")
    assert resp.status_code == 404


def test_delete_todo(client):
    client.post("/todos", json={"title": "Delete me"})
    resp = client.delete("/todos/1")
    assert resp.status_code == 200
    assert client.get("/todos/1").status_code == 404


def test_delete_nonexistent(client):
    # BUG: currently returns 200, should return 404
    resp = client.delete("/todos/999")
    assert resp.status_code == 404


def test_list_todos(client):
    for i in range(1, 4):
        client.post("/todos", json={"title": f"Todo {i}"})
    resp = client.get("/todos")
    assert resp.status_code == 200
    assert resp.json["total"] == 3
    assert len(resp.json["todos"]) == 3


def test_list_pagination(client):
    for i in range(1, 6):
        client.post("/todos", json={"title": f"Todo {i}"})
    # offset=1, limit=2 should return todos at index 1 and 2 (ids 2 and 3)
    resp = client.get("/todos?offset=1&limit=2")
    assert resp.status_code == 200
    todos = resp.json["todos"]
    # BUG: off-by-one returns wrong slice
    assert len(todos) == 2
    assert todos[0]["id"] == 2
    assert todos[1]["id"] == 3
