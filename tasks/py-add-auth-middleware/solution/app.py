from flask import Flask, jsonify
from middleware import require_auth

app = Flask(__name__)


@app.route("/data")
@require_auth
def get_data():
    return jsonify({"items": ["a", "b", "c"]})


if __name__ == "__main__":
    app.run()
