from flask import Flask, jsonify, request
from models import User
from routes.products import products_bp

app = Flask(__name__)
app.register_blueprint(products_bp)


@app.route("/users", methods=["GET"])
def get_users():
    return jsonify(User.all())


@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    u = User(data["name"], data["email"])
    return jsonify(u.to_dict()), 201
