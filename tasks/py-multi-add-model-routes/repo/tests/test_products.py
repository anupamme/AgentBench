import pytest
from app import app
from models import Product


@pytest.fixture(autouse=True)
def reset():
    Product.reset()
    yield
    Product.reset()


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_get_products_empty(client):
    resp = client.get("/products")
    assert resp.status_code == 200
    assert resp.json == []


def test_create_product(client):
    resp = client.post("/products", json={"name": "Widget", "price": 9.99})
    assert resp.status_code == 201
    assert resp.json["name"] == "Widget"
    assert resp.json["price"] == 9.99
    assert "id" in resp.json


def test_get_products_after_create(client):
    client.post("/products", json={"name": "Gadget", "price": 14.99})
    resp = client.get("/products")
    assert len(resp.json) == 1


def test_create_product_missing_price(client):
    resp = client.post("/products", json={"name": "Thing"})
    assert resp.status_code == 400
