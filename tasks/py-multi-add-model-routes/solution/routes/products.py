from flask import Blueprint, jsonify, request
from models import Product

products_bp = Blueprint("products", __name__)


@products_bp.route("/products", methods=["GET"])
def get_products():
    return jsonify(Product.all())


@products_bp.route("/products", methods=["POST"])
def create_product():
    data = request.get_json()
    if not data or "name" not in data or "price" not in data:
        return jsonify({"error": "name and price required"}), 400
    p = Product(data["name"], float(data["price"]))
    return jsonify(p.to_dict()), 201
