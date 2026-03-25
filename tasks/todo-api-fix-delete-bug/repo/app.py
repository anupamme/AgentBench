"""Flask application factory for the TODO API."""
from flask import Flask

from routes import todos_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(todos_bp)
    return app


if __name__ == "__main__":
    create_app().run(debug=True)
