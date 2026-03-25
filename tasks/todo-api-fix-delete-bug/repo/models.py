"""In-memory store for TODO items."""
from __future__ import annotations


class TodoStore:
    def __init__(self) -> None:
        self._todos: list[dict] = []
        self._next_id: int = 1

    def add(self, title: str, done: bool = False) -> dict:
        todo = {"id": self._next_id, "title": title, "done": done}
        self._next_id += 1
        self._todos.append(todo)
        return todo

    def get(self, todo_id: int) -> dict | None:
        for todo in self._todos:
            if todo["id"] == todo_id:
                return todo
        return None

    def delete(self, todo_id: int) -> bool:
        for i, todo in enumerate(self._todos):
            if todo["id"] == todo_id:
                self._todos.pop(i)
                return True
        # BUG: should return False here, but falls through and returns None
        # which is falsy — however routes.py doesn't check the return value

    def list_todos(self, offset: int = 0, limit: int = 20) -> list[dict]:
        # BUG: off-by-one — uses offset+1 instead of offset
        return self._todos[offset + 1 : offset + 1 + limit]

    def count(self) -> int:
        return len(self._todos)
