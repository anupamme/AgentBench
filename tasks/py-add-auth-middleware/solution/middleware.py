import functools

import jwt
from flask import jsonify, request

SECRET_KEY = "test-secret"


def require_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing token"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify({"error": "invalid token"}), 403
        return f(*args, **kwargs)

    return decorated
