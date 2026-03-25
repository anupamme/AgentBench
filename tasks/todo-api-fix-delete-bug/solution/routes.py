"""Route definitions for the TODO API."""
from flask import Blueprint, jsonify, request

from models import TodoStore

todos_bp = Blueprint("todos", __name__)
store = TodoStore()


@todos_bp.route("/todos", methods=["GET"])
def list_todos():
    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 20, type=int)
    items = store.list_todos(offset=offset, limit=limit)
    return jsonify({"todos": items, "total": store.count()})


@todos_bp.route("/todos", methods=["POST"])
def create_todo():
    data = request.get_json(force=True)
    if not data or "title" not in data:
        return jsonify({"error": "title is required"}), 400
    todo = store.add(title=data["title"], done=data.get("done", False))
    return jsonify(todo), 201


@todos_bp.route("/todos/<int:todo_id>", methods=["GET"])
def get_todo(todo_id: int):
    todo = store.get(todo_id)
    if todo is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(todo)


@todos_bp.route("/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(todo_id: int):
    deleted = store.delete(todo_id)
    if not deleted:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": todo_id}), 200
